#!/bin/bash
# Process supervision for the streamer pod. Sourced by entrypoint.sh (and by
# tests/test_supervisor.py, which stubs start_ffmpeg, backoff_sleep and
# report_event). Defines functions only.
#
#   ffmpeg_loop          run start_ffmpeg (defined by the caller; it must
#                        start ffmpeg in the background and set FFMPEG_PID,
#                        and RELAY_PID when input_relay.py feeds ffmpeg)
#                        forever, with backoff between runs
#   supervise NAME CMD   run CMD forever, with the same backoff
#
# Both are meant to run in their own background subshell (`ffmpeg_loop &`);
# SIGTERM to that subshell stops its child and ends the loop.

# First retry delay; doubled after every quick exit up to the max.
FFMPEG_RETRY_DELAY="${FFMPEG_RETRY_DELAY:-2}"
# Liveness (/live) never restarts the pod during an upstream outage, so this
# loop is the only recovery; at most 20 s keeps the gap short.
FFMPEG_MAX_RETRY_DELAY="${FFMPEG_MAX_RETRY_DELAY:-20}"
# A run (or helper) that lasted this long was healthy: the backoff restarts
# from the first delay instead of staying at the max forever.
FFMPEG_STABLE_RUN="${FFMPEG_STABLE_RUN:-60}"
HELPER_RETRY_DELAY="${HELPER_RETRY_DELAY:-2}"
HELPER_MAX_RETRY_DELAY="${HELPER_MAX_RETRY_DELAY:-30}"
SCRIPTS_DIR="${SCRIPTS_DIR:-/app/scripts}"
FFMPEG_PID="${FFMPEG_PID:-}"
RELAY_PID="${RELAY_PID:-}"
# Left by input_relay.py when it cannot read the upstream (a playlist, an
# ICY status line...) and ffmpeg may.
export RELAY_UNSUPPORTED_FLAG="${RELAY_UNSUPPORTED_FLAG:-/tmp/input_relay_unsupported}"

# ffmpeg_input_mode: how the next ffmpeg run reads the station
# (FFMPEG_INPUT_RECONNECT), where relay falls back to inprocess once the
# relay found an upstream only ffmpeg can read: it leaves
# RELAY_UNSUPPORTED_FLAG behind for the container's life.
ffmpeg_input_mode() {
    local mode="${FFMPEG_INPUT_RECONNECT:-inprocess}"
    if [ "$mode" = relay ] && [ -e "$RELAY_UNSUPPORTED_FLAG" ]; then
        mode=inprocess
    fi
    echo "$mode"
}

# next_retry_delay DELAY MAX: DELAY doubled, at most MAX.
next_retry_delay() {
    local doubled=$(( $1 * 2 ))
    echo $(( doubled > $2 ? $2 : doubled ))
}

# Fire-and-forget PostHog event; never blocks or fails the caller.
report_event() {
    python3 "$SCRIPTS_DIR/report_event.py" "$@" >/dev/null 2>&1 &
}

# Interruptible sleep: a SIGTERM trap runs at once instead of after it.
backoff_sleep() {
    sleep "$1" &
    wait $! || true
}

# stop_child PID: SIGTERM, then wait so the child is not orphaned.
stop_child() {
    [ -n "$1" ] || return 0
    kill -TERM "$1" 2>/dev/null || return 0
    wait "$1" 2>/dev/null || true
}

ffmpeg_loop() {
    local delay=$FFMPEG_RETRY_DELAY restarts=0 started_at ran_for exit_code
    local relay_code
    # The relay first: ffmpeg waiting on a silent pipe ignores SIGTERM
    # until its input ends.
    trap 'stop_child "$RELAY_PID"; stop_child "$FFMPEG_PID"; exit 0' TERM
    while true; do
        started_at=$(date +%s)
        RELAY_PID=""
        start_ffmpeg
        exit_code=0
        # `wait PID || true; code=$?` always yielded 0; keep the real code.
        wait "$FFMPEG_PID" || exit_code=$?
        relay_code=""
        if [ -n "$RELAY_PID" ]; then
            # The relay ends with ffmpeg (or ended first, the upstream lost).
            relay_code=0
            wait "$RELAY_PID" || relay_code=$?
        fi
        ran_for=$(( $(date +%s) - started_at ))
        restarts=$(( restarts + 1 ))
        if [ "$ran_for" -ge "$FFMPEG_STABLE_RUN" ]; then
            delay=$FFMPEG_RETRY_DELAY
        fi
        echo "ffmpeg_loop: ffmpeg exited (code=${exit_code}${RELAY_PID:+, relay=$relay_code}, ran=${ran_for}s, restart_count=${restarts}); retrying in ${delay}s"
        report_event ffmpeg_exit \
            --prop exit_code="$exit_code" \
            --prop ran_for="$ran_for" \
            --prop restart_count="$restarts" \
            --prop retry_delay="$delay" \
            --prop input_mode="${FFMPEG_INPUT_MODE:-}" \
            ${RELAY_PID:+--prop "relay_exit_code=$relay_code"}
        if [ -n "$RELAY_PID" ] && [ -e "$RELAY_UNSUPPORTED_FLAG" ]; then
            # Once: the next runs are inprocess.
            report_event relay_unsupported \
                --prop reason="$(cat "$RELAY_UNSUPPORTED_FLAG")"
        fi
        backoff_sleep "$delay"
        delay=$(next_retry_delay "$delay" "$FFMPEG_MAX_RETRY_DELAY")
    done
}

# supervise NAME CMD...: restart a helper whenever it exits. Without it a
# crashed helper (rewriter, metadata monitor, health server) stayed dead
# until the pod was replaced; only nginx was waited on.
supervise() {
    local name=$1
    shift
    local delay=$HELPER_RETRY_DELAY child="" started_at ran_for code
    trap 'stop_child "$child"; exit 0' TERM
    while true; do
        started_at=$(date +%s)
        "$@" &
        child=$!
        code=0
        wait "$child" || code=$?
        ran_for=$(( $(date +%s) - started_at ))
        if [ "$ran_for" -ge "$FFMPEG_STABLE_RUN" ]; then
            delay=$HELPER_RETRY_DELAY
        fi
        echo "supervise: ${name} exited (code=${code}, ran=${ran_for}s); restarting in ${delay}s"
        report_event helper_exit \
            --prop helper="$name" \
            --prop exit_code="$code" \
            --prop ran_for="$ran_for"
        backoff_sleep "$delay"
        delay=$(next_retry_delay "$delay" "$HELPER_MAX_RETRY_DELAY")
    done
}

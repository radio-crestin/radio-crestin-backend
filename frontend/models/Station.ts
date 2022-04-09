import mongoose, {Schema} from 'mongoose';
import {Station as StationType} from "../types";

const stationSchema = new Schema<StationType>({
  _id: {type: String, required: true},
  order: {type: Number, required: true},
  title: {type: String, required: true},
  website: {type: String, required: true},
  contact: {type: String, required: true},
  streamUrl: {type: String, required: true},
  thumbnailUrl: {type: String, required: true},
  groups: {type: [String], required: true},

  stats: {
    timestamp: {type: String, required: false},
    current_song: {
      songName: {type: String, required: false},
      artist: {type: String, required: false},
    },
    listeners: {type: Number, required: false},
    rawData: {type: Object, required: false},
    error: {type: Object, required: false},
  },

  uptime: {
    up: {type: Boolean, required: false},
    latencyMs: {type: Number, required: false},
    statusMessage: {type: String, required: false},
  },

  metadataEndpoint: {
    shoutcastStatsUrl: {type: String, required: false},
    oldIcecastHtmlStatsUrl: {type: String, required: false},
    icecastStatsUrl: {type: String, required: false},
    radioCoStatsUrl: {type: String, required: false},
    shoutcastXmlStatsUrl: {type: String, required: false},
    oldShoutcastStatsHtmlUrl: {type: String, required: false},
  }
});

export const StationModel = mongoose.models.Station || mongoose.model('Station', stationSchema)

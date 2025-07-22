# Backup Management Makefile
# 
# This Makefile provides convenient commands for creating and restoring backups
# using the Django management commands.

# Configuration
BACKUP_DIR = ../../../backups
BACKUP_FILE = $(BACKUP_DIR)/backup.zip
BACKUP_TYPE = all_models
MANAGE_PY = ../../../manage.py

# Default target
.PHONY: help
help:
	@echo "Available commands:"
	@echo "  backup           - Create a backup with all models"
	@echo "  backup-essential - Create a backup with essential data only"
	@echo "  restore          - Restore from backup.zip"
	@echo "  restore-clean    - Restore from backup.zip with cleanup"
	@echo "  clean            - Remove backup files"
	@echo ""
	@echo "Configuration:"
	@echo "  BACKUP_DIR  = $(BACKUP_DIR)"
	@echo "  BACKUP_FILE = $(BACKUP_FILE)"
	@echo "  BACKUP_TYPE = $(BACKUP_TYPE)"

# Create backup directory if it doesn't exist
$(BACKUP_DIR):
	mkdir -p $(BACKUP_DIR)

# Create backup with all models
.PHONY: backup
backup: $(BACKUP_DIR)
	@echo "Creating backup with all models..."
	python $(MANAGE_PY) create_backup --file $(BACKUP_FILE) --backup-type all_models
	@echo "Backup created successfully at $(BACKUP_FILE)"

# Create backup with essential data only
.PHONY: backup-essential
backup-essential: $(BACKUP_DIR)
	@echo "Creating backup with essential data..."
	python $(MANAGE_PY) create_backup --file $(BACKUP_DIR)/backup-essential.zip --backup-type essential_data
	@echo "Essential backup created successfully at $(BACKUP_DIR)/backup-essential.zip"

# Restore from backup
.PHONY: restore
restore:
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "Error: Backup file $(BACKUP_FILE) does not exist"; \
		exit 1; \
	fi
	@echo "Restoring from backup..."
	python $(MANAGE_PY) restore_backup --file $(BACKUP_FILE) --backup-type $(BACKUP_TYPE)
	@echo "Restore completed successfully"

# Restore from backup with cleanup
.PHONY: restore-clean
restore-clean:
	@if [ ! -f "$(BACKUP_FILE)" ]; then \
		echo "Error: Backup file $(BACKUP_FILE) does not exist"; \
		exit 1; \
	fi
	@echo "Restoring from backup with cleanup of existing data..."
	python $(MANAGE_PY) restore_backup --file $(BACKUP_FILE) --backup-type $(BACKUP_TYPE) --cleanup-existing-data
	@echo "Restore with cleanup completed successfully"

# Clean backup files
.PHONY: clean
clean:
	@echo "Cleaning backup files..."
	rm -f $(BACKUP_DIR)/*.zip
	@echo "Backup files cleaned"

# Show backup file info
.PHONY: info
info:
	@echo "Backup Information:"
	@echo "=================="
	@if [ -f "$(BACKUP_FILE)" ]; then \
		echo "Backup file: $(BACKUP_FILE)"; \
		echo "File size: $$(du -h $(BACKUP_FILE) | cut -f1)"; \
		echo "Last modified: $$(stat -f '%Sm' $(BACKUP_FILE))"; \
	else \
		echo "No backup file found at $(BACKUP_FILE)"; \
	fi

# List available backup types
.PHONY: types
types:
	@echo "Available backup types (from settings.py):"
	@echo "- all_models: Backup all models"
	@echo "- essential_data: Backup essential data only"
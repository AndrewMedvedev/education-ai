RESTORE_TIMESTAMP ?= latest

restore:
	@if [ "$(RESTORE_TIMESTAMP)" = "latest" ]; then \
		TIMESTAMP=$$(ls -t ./backups/postgres_*.dump | head -1 | sed 's/.*postgres_//; s/\.dump//'); \
	else \
		TIMESTAMP=$(RESTORE_TIMESTAMP); \
	fi; \
	echo "Restoring from $$TIMESTAMP"; \
	bash ./scripts/restore.sh $$TIMESTAMP

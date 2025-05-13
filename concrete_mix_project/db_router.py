# concrete_mix_project/db_router.py

class CdbRouter:
    APP_LABEL = "cdb_app"  # The name of our new app

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "cdb"  # Use 'cdb' database for models in cdb_app
        return None  # Use 'default' for other apps

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.APP_LABEL:
            return "cdb"  # Use 'cdb' database for models in cdb_app
        return None  # Use 'default' for other apps

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.APP_LABEL:
            # Allow migrations for cdb_app only on the 'cdb' database
            return db == "cdb"
        # Allow migrations for other apps only on the 'default' database
        return db == "default"

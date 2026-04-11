try:
    from .bom_creator import BOMCreatorPlugin
    BOMCreatorPlugin().register()
except Exception as e:
    import logging
    logging.error(f"Failed to load BOM Creator plugin: {e}")
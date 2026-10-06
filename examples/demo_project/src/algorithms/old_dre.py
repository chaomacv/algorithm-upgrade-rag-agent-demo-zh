class OldDRE:
    name = "old_dre"

    def process(self, image):
        """Return the legacy DRE output schema with residual_map."""
        # Downstream code depends on all three returned fields.
        return {
            "image": image * 1.0,
            "residual_map": 0.1,
            "metadata": {
                "algorithm": self.name
            }
        }

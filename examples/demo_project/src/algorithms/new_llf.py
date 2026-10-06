class NewLLF:
    name = "new_llf"

    def process(self, image):
        """Return the new algorithm output that lacks residual_map."""
        # The missing field is deliberate so the adapter fix is necessary.
        return {
            "image": image * 1.1,
            "metadata": {
                "algorithm": self.name
            }
        }

from pipeline import Pipeline


def run():
    """Run the toy algorithm pipeline with its default configuration."""
    # The CLI and tests use this function as the runtime entry point.
    return Pipeline().run(image=1.0)


if __name__ == "__main__":
    print(run())

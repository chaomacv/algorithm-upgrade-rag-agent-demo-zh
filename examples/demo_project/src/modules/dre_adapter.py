def run_dre(algorithm, image):
    result = algorithm.process(image)
    if "residual_map" not in result:
        result["residual_map"] = 0.0
    return result

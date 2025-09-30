from calcula_resultados import compute_indicators_from_files


files = ["balancetes/balancete1.json"]
result = compute_indicators_from_files(files)

print(result)

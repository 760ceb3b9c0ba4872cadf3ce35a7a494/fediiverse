from fediiverse.nginx import build_configuration


def main():
	print("Updating nginx configuration based on config.json...")
	build_configuration(log=True)
	print(f"done!")


if __name__ == "__main__":
	main()

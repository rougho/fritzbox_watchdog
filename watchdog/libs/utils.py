import os
from .logger import log_info, log_warning, log_error


def load_env_file(env_file='.env'):
    """
    Loads environment variables from a specified .env file and sets them in the OS environment.

    Args:
        env_file (str): Path to the .env file. Defaults to '.env'.

    Behavior:
        - If the .env file does not exist, logs a warning and returns.
        - Reads each line of the file, ignoring comments and blank lines.
        - For lines containing an '=', splits into key and value, strips whitespace, and sets them as environment variables.
        - Logs a confirmation message upon successful loading.
        - Logs an error message if an exception occurs during loading.
    """
    if not os.path.exists(env_file):
        log_warning(
            f"{env_file} file not found. Using default/command line values.")
        return

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        log_info(f"Loaded configuration from {env_file}")
    except Exception as e:
        log_error(f"Error loading {env_file}: {e}")

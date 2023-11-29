from dynaconf import Dynaconf
import os

current_directory = os.path.dirname(os.path.realpath(__file__))

settings = Dynaconf(
    envvar_prefix="DYNACONF",  # export envvars with `export DYNACONF_FOO=bar`.
    settings_files=[f"{current_directory}/settings.yaml", f"{current_directory}/.secrets.yaml"],  # Loads files in the given order.
)
#!/bin/bash

# Setup base environment
EE="${HOME}/.envs/emit"
[ -d "$EE/lib/python3.10" ] || {
    printf "Installing to %s\n" "$EE"
    mkdir -p "$EE"
    python -m venv --without-pip --symlinks "$EE"
    printf "%s\n" "/env/lib/python3.10/site-packages" > "$EE"/lib/python3.10/site-packages/base_venv.pth

    if [ -z "$EARTHDATA_TOKEN" ]; then
        printf "EARTHDATA_TOKEN is not set, please set it before running this script\n"
        exit 1
    fi

    # Install Jupyter Kernel
    "$EE/bin/python" -m ipykernel install\
    --user \
    --name emit \
    --display-name emit \
    --env EARTHDATA_TOKEN "$EARTHDATA_TOKEN" \
    --env ODC_EMIT_DB_URL "postgresql:///datacube?host=/tmp"
 
    printf "Kernel:\n%s\n\n" "$(cat $HOME/.local/share/jupyter/kernels/emit/kernel.json)"
}


# Add extras
DEPS=(
    "odc-stac==0.3.10a1"
    "odc-geo>=0.4.2"
    "s3fs"
    "git+https://github.com/csiro-easi/emit"
    "git+https://github.com/opendatacube/datacube-core@f6ff8e24e2204ebc26b9040209cc565c9212dbc8"
)
"$EE/bin/python" -m pip install "${DEPS[@]}"
"$EE/bin/python" -m odc.emit info 

printf 'To activate:\n>>> source "%s/bin/activate"\n\n' "$EE"
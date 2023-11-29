#!/bin/bash
#
# Generate an SSHA password for .htpasswd files
# * https://www.nginx.com/resources/wiki/community/faq/#how-do-i-generate-an-htpasswd-file-without-having-apache-tools-installed
# * https://nginx.org/en/docs/http/ngx_http_auth_basic_module.html#auth_basic_user_file
#
if [ -z "$1" ]; then
        echo "Usage: $(basename $0) [user]"
        exit 1
else
        NAME="$1"
        read -p "Password: " -s PASSWORD
        echo
fi

SALT=$(openssl rand -base64 3)
SHA1=$(echo -n "${PASSWORD}${SALT}" | openssl dgst -binary -sha1 | xxd -p | sed "s/$/$(echo -n ${SALT} | xxd -p)/" | xxd -r -p | base64)
echo "$NAME:{SSHA}$SHA1"
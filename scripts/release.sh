#!/bin/bash

rm -rf dist/

python -m build

cd dist

fname=`ls | grep tar`
project_name=toxicnotifications

curl -F file=@$fname -F prefix=pypi/$project_name https://pypi.poraodojuca.dev -H "Authorization: Key $PYPI_AUTH_KEY"

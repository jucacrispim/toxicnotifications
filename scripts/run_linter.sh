#!/bin/bash

pylint toxicsecrets/
if [ $? != "0" ]
then
    exit 1;
fi

flake8 toxicsecrets/

if [ $? != "0" ]
then
    exit 1;
fi

flake8 tests
exit $?;

#!/bin/bash

echo -e "\033[32mRetrieving errors tested by $1 test cases\033[0m"
cd $1 && cat `ls | grep .err` | grep error
echo -e "\033[32mAll $1 error tests retrieved\033[0m"

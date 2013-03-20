#!/bin/bash

source config

# cleanup old screenshots
rm -f ./screenshots/*.png

function printlog() {
	echo "$1" | while read line ; do
		echo "$line" | grep -q "^++" && continue
		echo "  $line"
	done
	echo
}

count_test=0
count_ok=0
count_fail=0
count_error=0
count_skipped=0

function runtest() {
	dotcount=`echo "45 - ${#1}" | bc`
	dots=`seq -s "." $dotcount | sed 's/[0-9]//g'`
	echo -ne "\e[1mRunning\e[00m $1 $dots "
	let count_test=count_test+1
	testlog="`./tests/$1 2>&1`"
	res=$?

	if [ "$res" == "0" ] ; then
		# OK
		echo -e "\e[1;32mOK\e[00m"
		if [ "$DEBUG" == "1" ] ; then
			printlog "$testlog"
		fi
		let count_ok=count_ok+1
		return 0
	elif [ "$res" == "1" ] ; then
		# FAIL
		echo -e "\e[1;31mFAIL\e[00m"
		printlog "$testlog"
		let count_fail=count_fail+1
		return 1
	elif [ "$res" == "2" ] ; then
		# ERROR
		echo -e "\e[1;35mERROR\e[00m"
		printlog "$testlog"
		let count_error=count_error+1
		return 2
	elif [ "$res" == "3" ] ; then
		# SKIPPED
		echo -e "\e[1;33mSKIPPED\e[00m"
		if [ "$DEBUG" == "1" ] ; then
			printlog "$testlog"
		fi
		let count_skipped=count_skipped+1
		return 3
	else
		# WTF
		echo -e "\e[1;34mWTF?\e[00m"
		printlog "$testlog"
		return 4
	fi
}

starttime=`date +%s`
for testname in `ls ./tests` ; do
	if [ "$1" == "cleanup" ] ; then
		echo "$testname" | grep -v "nocleanup" | grep -q "cleanup" || continue
	elif [ "$1" == "nocleanup" ] ; then
		echo "$testname" | grep -q "cleanup" && continue
	fi
	runtest "$testname"
	ret=$?
	if [[ "[1]" =~ "$ret" ]] && [ "$BREAK_ON_FAIL" == "1" ] ; then
		break
	fi
done
endtime=`date +%s`

let timesec=endtime-starttime

duration_str=`date -ud @$timesec +%M:%S`

echo
echo "Ran $count_test tests in $duration_str"
printf " --> %2d ok\n"      $count_ok
printf " --> %2d fail\n"    $count_fail
printf " --> %2d errors\n"  $count_error
printf " --> %2d skipped\n" $count_skipped

if [ "$count_fail" == "0" ] ; then
	if [ "$count_ok" -gt "0" ] ; then
		exit 0
	else
		exit 2
	fi
else
	exit 1
fi

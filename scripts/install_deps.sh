#!/bin/bash

# get arguments
while getopts i:r: flag
do
  case "${flag}" in
    i) install_dir=${OPTARG};;
    r) run_dir=${OPTARG};;
  esac
done

# check for default values
if [[ -z "$install_dir" || ! -z `echo $install_dir | grep '^-'` ]]; then
  install_dir="$HOME/.spack-ci"
fi

if [[ -z "$run_dir" || ! -z `echo $run_dir | grep '^-'` ]]; then
  run_dir=`pwd`
fi

# print out arguments
echo "Run Directory: $run_dir";

# go to directory
cd $run_dir

# install spack environment
echo "::group::Install Spack Packages"
. spack/share/spack/setup-env.sh
spack --color always -e $run_dir/. install -j3 --deprecated --no-checksum
exc=$?
if [ $exc -ne 0 ]; then
  echo "Error in installing dependencies! exit code is $exc ..."
  exit $exc
fi
echo "::endgroup::"

# output esmf.mk file for debugging
echo "::group::Content of esmf.mk"
cat $install_dir/view/lib/esmf.mk
echo "::endgroup::"

#!/bin/bash

# get arguments
while getopts a:d:i:m:n: flag
do
  case "${flag}" in
    a) app_install_dir=${OPTARG};; 
    d) data_comp=${OPTARG};;
    i) deps_install_dir=${OPTARG};;
    m) model_comp=${OPTARG};;
    n) model_module=${OPTARG};;
  esac
done

# check for default values
if [[ -z "$app_install_dir" || ! -z `echo $app_install_dir | grep '^-'` ]]; then
  app_install_dir="$HOME/app"
fi

if [ -z "$data_comp" ]; then
  echo "Name of data component is not given! Exiting ..."
  exit
fi

if [ ! -z `echo $data_comp | grep '^-'` ]; then
  echo "argument -d is given but name of data component is not given!"
  echo "valid values are datm, docn, dlnd, dwav, drof, dice"
  exit
fi

if [[ -z "$deps_install_dir" || ! -z `echo $deps_install_dir | grep '^-'` ]]; then
  deps_install_dir="$HOME/.spack-ci"
fi

if [ -z "$model_comp" ]; then
  echo "Name of model component is not given! Exiting ..."
  exit
fi

if [ ! -z `echo $model_comp | grep '^-'` ]; then
  echo "argument -m is given but name of model component is not given!"
  exit
fi

if [ -z "$model_module" ]; then
  echo "Name of model module is not given! Exiting ..."
  exit
fi

if [ ! -z `echo $model_module | grep '^-'` ]; then
  echo "argument -n is given but name of model module is not given!"
  exit
fi

# set required environment variables
export PATH=$deps_install_dir/view/bin:$PATH
export ESMFMKFILE=$deps_install_dir/view/lib/esmf.mk
export ESMF_ESMXDIR=$deps_install_dir/view/include/ESMX

# go to application build directory
cd $app_install_dir
echo "::group::Content of The Installation Directory"
echo "### $app_install_dir ###"
ls $app_install_dir
echo "### $app_install_dir/include ###"
ls $app_install_dir/include
echo "### $app_install_dir/lib ###"
ls $app_install_dir/lib
echo "::endgroup::"

# create YAML file for build
echo "application:" >> esmxBuild.yaml
echo "  disable_comps: ESMX_Data" >> esmxBuild.yaml
echo "  link_paths: $deps_install_dir/view/lib" >> esmxBuild.yaml 
echo "  link_libraries: piof" >> esmxBuild.yaml
echo "" >> esmxBuild.yaml
echo "components:" >> esmxBuild.yaml
echo "  $data_comp:" >> esmxBuild.yaml
echo "    build_type: none" >> esmxBuild.yaml
echo "    install_prefix: $app_install_dir" >> esmxBuild.yaml
echo "    libraries: $data_comp dshr streams cdeps_share" >> esmxBuild.yaml
echo "    fort_module: cdeps_${data_comp}_comp.mod" >> esmxBuild.yaml
echo "  $model_comp:" >> esmxBuild.yaml
echo "    build_type: none" >> esmxBuild.yaml
echo "    install_prefix: $app_install_dir" >> esmxBuild.yaml
echo "    fort_module: $model_module" >> esmxBuild.yaml
cat esmxBuild.yaml

# create build directory
ESMX_Builder
exc=$?
if [ $exc -ne 0 ]; then
  echo "Error when creating executable! exit code is $exc ..."
  exit $exc
fi

# compile and create executable
cd $app_install_dir/build
make

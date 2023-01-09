#!/bin/bash

# get arguments
while getopts a:d:i:r: flag
do
    case "${flag}" in
        a) arch=${OPTARG};;
        d) deps=${OPTARG};;
        i) install_dir=${OPTARG};;
        r) run_dir=${OPTARG};;
    esac
done

# check for default values
if [ -z "$deps" ]; then
  echo "Dependencies are not given! Exiting ..."
  exit
fi

if [ ! -z `echo $deps | grep '^-'` ]; then
  echo "argument -d is given but dependencies are not listed!"
  exit
fi
if [[ -z "$install_dir" || ! -z `echo $install_dir | grep '^-'` ]]; then
  install_dir="$HOME/.spack-ci"
fi

if [[ -z "$run_dir" || ! -z `echo $run_dir | grep '^-'` ]]; then
  run_dir=`pwd`
fi

if [[ -z "$arch" || ! -z `echo $arch | grep '^-'` ]]; then
  arch="x86_64_v4"
fi

# print out arguments
echo "Target Architecture: $arch"
echo "Dependencies: $deps";
echo "Install Directory: $install_dir";
echo "Run Directory: $run_dir";

# go to directory
cd $run_dir

# checkout spack
echo "::group::Checkout Spack"
git clone -b jcsda_emc_spack_stack https://github.com/NOAA-EMC/spack.git
echo "::endgroup::"

# create spack.yaml
echo "::group::Create spack.yaml"
echo "spack:" > spack.yaml
echo "  concretizer:" >> spack.yaml
echo "    targets:" >> spack.yaml
echo "      granularity: generic" >> spack.yaml
echo "      host_compatible: false" >> spack.yaml
echo "    unify: when_possible" >> spack.yaml
echo "  specs:" >> spack.yaml
IFS=', ' read -r -a array <<< "$deps"
for d in "${array[@]}"
do
  echo "  - $d target=$arch" >> spack.yaml
done
echo "  packages:" >> spack.yaml
echo "    all:" >> spack.yaml
# following is required to build same optimized spack for different github action runners
# spack arch --known-targets command can be used to list known targets
echo "      target: ['$arch']" >> spack.yaml
# following fixes compiler version
echo "      compiler: [gcc@11.3.0]" >> spack.yaml
echo "  view: $install_dir/view" >> spack.yaml
echo "  config:" >> spack.yaml
echo "    source_cache: $install_dir/source_cache" >> spack.yaml
echo "    misc_cache: $install_dir/.spack-ci/misc_cache" >> spack.yaml
echo "    test_cache: $install_dir/test_cache" >> spack.yaml
echo "    install_tree:" >> spack.yaml
echo "      root: $install_dir/opt" >> spack.yaml
cat spack.yaml
echo "::endgroup::"

# concretize spack environment
echo "::group::Concretize Spack Environment Using YAML Specification"
. spack/share/spack/setup-env.sh
spack --color always -e $run_dir/. concretize -f
echo "::endgroup::"

# install spack environment
echo "::group::Install Spack Packages"
spack --color always -e $run_dir/. install -j3 --deprecated --no-checksum
echo "::endgroup::"

# return output
#echo "::set-output name=version::spack-$arch-`"
#spack-${{ steps.build-env.outputs.SPACK_ARCH }}-${{ hashFiles('**/spack.lock') }}

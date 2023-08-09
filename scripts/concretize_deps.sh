#!/bin/bash

# get arguments
while getopts a:c:d:i:r: flag
do
  case "${flag}" in
    a) arch=${OPTARG};;
    c) comp=${OPTARG};;
    d) deps="${OPTARG}";;
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
  arch="x86_64"
fi

if [[ -z "$comp" || ! -z `echo $comp | grep '^-'` ]]; then
  comp="11.4.0"
fi

# print out arguments
echo "Target Architecture: $arch"
echo "Compiler: $comp"
echo "Dependencies: $deps";
echo "Install Directory: $install_dir";
echo "Run Directory: $run_dir";

# go to directory
cd $run_dir

# checkout spack and setup to use it
echo "::group::Checkout Spack"
git clone https://github.com/spack/spack.git
. spack/share/spack/setup-env.sh
echo "::endgroup::"

# find compilers
spack compiler find
cat ~/.spack/linux/compilers.yaml
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
IFS=':' read -r -a array <<< "$deps"
for d in "${array[@]}"
do
  echo "  - $d %$comp target=$arch" >> spack.yaml
done
echo "  packages:" >> spack.yaml
echo "    all:" >> spack.yaml
# following is required to build same optimized spack for different github action runners
# spack arch --known-targets command can be used to list known targets
echo "      target: ['$arch']" >> spack.yaml
echo "      compiler: [$comp]" >> spack.yaml
echo "  view: $install_dir/view" >> spack.yaml
echo "  config:" >> spack.yaml
echo "    source_cache: $install_dir/source_cache" >> spack.yaml
echo "    misc_cache: $install_dir/misc_cache" >> spack.yaml
echo "    test_cache: $install_dir/test_cache" >> spack.yaml
echo "    install_tree:" >> spack.yaml
echo "      root: $install_dir/opt" >> spack.yaml
echo "    install_missing_compilers: true" >> spack.yaml
cat spack.yaml
echo "::endgroup::"

# find external tools
echo "::group::Find Externals"
spack external find
echo "::endgroup::"

# create config file (to fix FetchError issue)
echo "::group::Create config.yaml"
echo "config:" > ~/.spack/config.yaml
echo "  url_fetch_method: curl" >> ~/.spack/config.yaml
echo "  connect_timeout: 60" >> ~/.spack/config.yaml
cat ~/.spack/config.yaml
echo "::endgroup::"

# concretize spack environment
echo "::group::Concretize Spack Environment Using YAML Specification"
spack --color always -e $run_dir/. concretize -f
exc=$?
if [ $exc -ne 0 ]; then
  echo "Error in concretizing dependencies! exit code is $exc ..."
  exit $exc
fi
echo "::endgroup::"

import os
import re
import sys
import yaml
import argparse
import collections
try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper
from paramgen import ParamGen

def expand_func(varname):
    my_dict = {}

    # loop over list
    for var in glob_list:
        env_var = os.environ.get(var)
        if env_var is not None:
            my_dict[var] = '{}'.format(os.getenv(var))
        else:
            my_dict[var] = ''

    return my_dict[varname]

def read_drv_yaml_file(file_path):
    # open yaml file and read it
    if not os.path.exists(file_path):
        sys.exit('File not found: {}'.format(file_path))
    with open(file_path) as _file:
        data = yaml.load(_file, Loader=Loader)
        return dict({k.lower().replace("-", "_"): v for k, v in data.items()})

def gen_config(_dict, ifile):
    # global variable which is used by expand_func
    global glob_list
    glob_list = []

    # data structure to keep tracking file open mode
    append = {}

    # loop over components read component specific YAML files
    ga = False
    for k1, v1 in _dict['components'].items():
        if 'drv' == k1:
            # get driver content
            _dict_comp = _dict['components'][k1] 

            # check configuration for generalAttributes
            if 'generalAttributes' in _dict_comp['config']['hconfig']['content'].keys():
                ga = True

            # get driver config file
            if 'nuopc' in _dict_comp['config']:
                drv_config_file = _dict_comp['config']['nuopc']['name']
            elif 'hconfig' in _dict_comp['config']:
                drv_config_file = _dict_comp['config']['hconfig']['name']
            else:
                sys.exit("config section requires nuopc or hconfig in {}! exiting ...".format(ifile))
        else:
            # read component YAML file
            if os.path.isabs(os.path.dirname(v1)): # absolute path is used
                _dict_comp = read_drv_yaml_file(v1)
            else: # relative path is used
                _dict_comp = read_drv_yaml_file(os.path.join(os.path.dirname(ifile), v1))                

        # loop over config/s
        if 'config' in _dict_comp:
            for k2, v2 in _dict_comp['config'].items():
                # set name for output file
                if 'name' in v2:
                    ofile = v2['name']
                else:
                    sys.exit("name is not given for '{}:{}' config section!".format(k1, k2))

                # append to file or not
                k3 = '{}_{}'.format(k2, ofile)
                if k3 in append:
                    append[k3] = True 
                else:
                    append[k3] = False
              
                # process content of config file
                glob_list.clear()
                if 'content' in v2:
                    # pass content to ParamGen
                    pg = ParamGen(v2['content'])

                    # loop over data and find dynamic variables like ${VAR}
                    for k4, v4 in pg.data.items():
                        for k5, v5 in v4.items():
                            if isinstance(v5, dict):
                                key, val = list(v5.items())[0]
                                if 'values' in key:
                                    glob_list = add_to_list(v5, glob_list)
                                else:
                                    for k6, v6 in v5.items():
                                        if 'values' in v6:
                                            glob_list = add_to_list(v6, glob_list)
                                        else:
                                            for k7, v7 in v6.items():
                                                glob_list = add_to_list(v7, glob_list)
                            else:
                                glob_list = add_to_list(v5, glob_list)

                    # remove duplicates from list
                    glob_list = list(set(glob_list))

                    # replace dynamic variables with environment ones
                    pg.reduce(expand_func)

                    # write config file in specified format
                    if 'nuopc' in k2:
                        pg.write_nuopc(ofile, append=append[k3])
                    elif 'nml' in k2:
                        pg.write_nml(ofile, append=append[k3])
                    elif 'hconfig' in k2:
                        pg.write_hconfig(ofile, append=append[k3], ga=ga)
                    else:
                        sys.exit("{} format for config file is not supported!".format(k2))
                else:
                    sys.exit("content is not given for '{}:{}' config section!".format(k1, k2))

def add_to_list(_val, _list):
    # convert to string
    value_str = str(_val['values']).strip()

    # find start and end indices of each occurance
    sind = [i for i in range(len(value_str)) if value_str.startswith('${', i)]
    eind = [i+1 for i in range(len(value_str)) if value_str.startswith('}', i)]

    # loop over them and create dictionary
    for i, j in zip(sind, eind):
        env_var = value_str[i:j].replace('${', '').replace('}', '')
        _list.append(env_var)
    return(_list)

def main(argv):
    # default values
    ifile = 'nuopc_drv.yaml'
    odir = '.'

    # read input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--ifile' , help='Input YAML file')
    parser.add_argument('--odir'  , help='Output directory')
    args = parser.parse_args()

    if args.ifile:
        ifile = args.ifile
    if args.odir:
        odir = args.odir

    # read configuration YAML file
    _dict = read_drv_yaml_file(ifile)

    # generate configuration files
    gen_config(_dict, ifile)

if __name__== "__main__":
    main(sys.argv[1:])

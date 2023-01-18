try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader, Dumper

import os
import sys
import yaml
import argparse
import collections
import hashlib
import ftplib
import boto3
from botocore import UNSIGNED
from botocore.client import Config

def read_drv_yaml_file(file_path):
    # open yaml file and read it
    if not os.path.exists(file_path):
        sys.exit('File not found: {}'.format(file_path))
    with open(file_path) as _file:
        data = yaml.load(_file, Loader=Loader)
        return dict({k.lower().replace("-", "_"): v for k, v in data.items()})

def recv_files(_dict, fhash, force_download):
    # loop through available components
    for k1, v1 in _dict.items():
        # query protocol, end_point and also list of files
        if 'protocol' in v1['input']:
            protocol = v1['input']['protocol']
        else:
            sys.exit('No protocol is specified for {} component'.format(k1))

        if 'end_point' in v1['input']:
            end_point = v1['input']['end_point']
        else:
            sys.exit('No end_point is specified for {} component'.format(k1))

        if 'files' in v1['input']:
            files = v1['input']['files']
        else:
            sys.exit('Files are not listed for {} component'.format(k1))

        # save current directory
        current_dir = os.getcwd()

        # check if target directory specified and change the directory to it
        if 'target_directory' in v1['input']:
            # set target directory
            target_dir = os.path.join(current_dir, v1['input']['target_directory'])

            # check directory
            if not os.path.isdir(target_dir):
                # create directory
                os.mkdir(target_dir)

            # change the current directory
            os.chdir(target_dir)

        # call data retrieval routine for component
        print('downloading files using {} protocol ...'.format(protocol))
        if protocol == 'ftp':
            ftp_get(end_point, files, fhash, force_download)
        if protocol == 'wget':
            cmd_get(end_point, files, fhash, force_download)
        elif protocol == 's3':
            s3_get(end_point, files, fhash, force_download)
        elif protocol == 's3-cli':
            s3_cli_get(end_point, files, fhash, force_download)
        else:
            sys.exit("unsupported protocol to download data: {}".format(protocol))

        # back to the saved current directory
        os.chdir(current_dir)

def ftp_get(end_point, files, fhash, force_download):
    # loop over files
    for f in files:
        lfile = os.path.basename(f)

        # open connection to server
        ftp = ftplib.FTP(end_point)
        ftp.login()

        # download file
        with open(lfile, "wb") as fout:
            if os.path.exists(lfile) and not force_download:
                print('file \'{}\' is found. skip downloading'.format(lfile))
            else:
                print('downloading {}'.format(lfile)) 
                ftp.retrbinary(f"RETR {f}", fout.write)

        # close connection
        ftp.quit()

        # get hash of file
        md5sum_local = hashlib.md5(open(lfile,'rb').read()).hexdigest()

        # write file name and checksum to file
        fhash.write('{}  {}\n'.format(md5sum_local, lfile))

def cmd_get(end_point, files, fhash, force_download):
    # loop over files
    for f in files:
        lfile = os.path.basename(f)

        # download file
        if force_download:
            cmd = 'wget --no-verbose --no-check-certificate {}:{}'.format(end_point, f)
        else:
            cmd = 'wget --no-verbose --no-check-certificate -c {}:{}'.format(end_point, f)
        print("cmd is {}".format(cmd))
        os.system(cmd)

        # get hash of file
        md5sum_local = hashlib.md5(open(lfile,'rb').read()).hexdigest()

        # write file name and checksum to file
        fhash.write('{}  {}\n'.format(md5sum_local, lfile))

def s3_cli_get(end_point, files, fhash, force_download):
    # loop over files
    for f in files:
        lfile = os.path.basename(f)

        # download file
        download = True
        if os.path.exists(lfile) and not force_download:
            print('file \'{}\' is found. skip downloading'.format(lfile))
            download = False 

        if download:
            cmd = 'aws s3 cp --no-sign-request s3://{}/{} .'.format(end_point, f)
            print("cmd is '{}'".format(cmd))
            os.system(cmd)

        # get hash of file
        md5sum_local = hashlib.md5(open(lfile,'rb').read()).hexdigest()

        # write file name and checksum to file
        fhash.write('{}  {}\n'.format(md5sum_local, lfile))    

def s3_get(end_point, files, fhash, force_download):
    # create an S3 access object, config option allows accessing anonymously
    s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))

    # loop over files
    for f in files:
        lfile = os.path.basename(f)

        # try to get checksum from s3 bucket
        try:
            print('end_point = {} and file = {}'.format(end_point, f))
            md5sum_remote = s3.head_object(Bucket=end_point, Key=f)['ETag'][1:-1]
        except botocore.exceptions.ClientError:
            md5sum_remote = None

        # try to get checksum from local file, if exists
        found = False
        if os.path.exists(lfile):
            found = True
            md5sum_local = hashlib.md5(open(lfile,'rb').read()).hexdigest()
        else:
            md5sum_local = None

        # download file if local file not found or checksums not matched
        download = False
        if not found:
            print('file not found \'{}\''.format(lfile))
            download = True
        else:
            if md5sum_remote != md5sum_local:
                print('file \'{}\' is found but checksums are not matched!\ns3   :{}\nlocal:{}'.format(lfile, md5sum_remote, md5sum_local))
                download = True
        if force_download:
            download = True
        if download:    
            print('downloading \'{}\''.format(lfile)) 
            s3.download_file(Bucket=end_point, Key=f, Filename=lfile)
        else:
            print('file \'{}\' is found. skip downloading'.format(lfile))

        # write file name and checksum to file
        fhash.write('{}  {}\n'.format(md5sum_remote, lfile))

def main(argv):
    # default values
    ifile = 'nuopc_drv.yaml'
    force_download = False

    # read input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--ifile' , help='Input driver yaml file', required=True)
    parser.add_argument('--force-download', help='Force to skip file checking', action='store_true')
    args = parser.parse_args()

    if args.ifile:
        ifile = args.ifile
    if args.force_download:
        force_download = args.force_download

    # read driver configuration yaml file and sort it
    _dict = read_drv_yaml_file(ifile)

    # sort based on components
    _dict = collections.OrderedDict(sorted(_dict['components'].items()))

    # remove driver from dictionary
    if not 'input' in _dict['drv']:
        _dict.pop('drv', None)

    # create copy of dictionary to loop over
    _dict_copy = _dict.copy()

    # loop over component YAML files and add it to dictionary
    for k1, v1 in _dict_copy.items():
        # skip if it is drv
        if k1 == 'drv':
            continue

        # set input file name
        if os.path.isabs(os.path.dirname(v1)): # absolute path is used
            input_file = v1
        else: # relative path is used
            input_file = os.path.join(os.path.dirname(ifile), v1)

        # check file and add it if it is found
        if os.path.isfile(input_file):
            # read component YAML file and add it to dictionary
            _dict_comp = read_drv_yaml_file(input_file)

            # add component info
            if 'input' in _dict_comp:
                _dict[k1] = _dict_comp
            else:
                _dict.pop(k1, None)
                print('There is no input section for {} component. Skip it!'.format(k1))
        else:
            sys.exit('File not found: {}'.format(input file))

    # open file object to store list of files and their hashes
    fhash = open('file_checksum.lock', 'w')

    # get files
    recv_files(_dict, fhash, force_download)

    # close file
    fhash.close()

if __name__== "__main__":
	main(sys.argv[1:])

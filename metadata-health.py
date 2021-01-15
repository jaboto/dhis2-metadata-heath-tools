import requests
import argparse
import json
import pprint
 

# Some constants
being_verbose = False
dry_run = False
 
def parse_arguments():
    parser = argparse.ArgumentParser(description="Metadata health checks for DHIS2 servers")
    parser.add_argument('-s', 
                        '--server_url', 
                        help='DHIS2 HTTP(s) server address without the API part', 
                        required=True)
    parser.add_argument('-u',
                        '--username', 
                        help='DHIS2 username',
                        required=True)
    parser.add_argument('-p', 
                        '--password', 
                        help='DHIS2 password', 
                        required=True)
    parser.add_argument('-n',
                        '--dry_run',
                        action='store_true',
                        help='If enabled no write actions will be performed')
    parser.add_argument('-v', 
                        '--verbose', 
                        action='store_true', 
                        help='Be verbose while executing the tasks')
    return parser.parse_args()
 
def be_verbose(message):
    # Print the string if we are in verbose mode
    if being_verbose:
        print(message)
 

def duplicated_UID(dry=True, fix=False):
    # Verify that there are no duplicated UIDs in the System. This will cause
    # problems with the Android Application
    # JIRA ref:
    #
    # This can only happen when performing manual modifications on the database
    # for the UIDs or by using import tools
    #
    # Check:
    #       Duplicated UIDs in all the metadata from the server
    # Available Fix:
    #       Not available, the user should manually modify the UID 
    metadata = api_caller('metadata.json?fields=id')
    # Metadata contains the information about the server which won't be needed
    metadata['system'] = []
    ids = []
    duplicated_ids = []
    for key,values in metadata.items():
        for v in values:
            try:
                id = v['id']
                if id in ids:
                    # Found a duplicated ID, this is really bad!
                    duplicated_ids.append(id)
                else:
                    ids.append(id)
            except Exception as e:
                print ("The received metadata is not OK. Something went wrong!")
                print (e)

    # If duplicates were found list them
    if len(duplicated_ids) > 0:
        print ("The following duplicates where found. Please verify!")
        print (duplicated_ids)
        print ("Probably you want to execute the following call to get more information")
        print ('{}/metadata.json?filter=id:in:[{}]'
                .format(api_url,','.join(duplicated_ids)))
    else:
        print ("No ID duplicates were found!")
    # TODO make an API call to identify them and present them beautifuly

    pprint.pprint(json)

def api_caller(api_call):
    # Perfrom an API call and return a dict with the content for valid requests
    # or false whenever there is an error with the reuqest (code != 200)
    api_request = '{}/{}'.format(api_url, api_call)
    be_verbose("Querying the API: "+api_request)

    try:
        r = requests.get(api_request, auth=(usr, pwd))
        if r.status_code == 200:
            return json.loads(r.content)
        elif r.status_code == 404:
            print("Error 404")
        else:
            print("Error UNKNOWN")
    except Exception as e:
        error_msg = "There was a problem with the API call: \n{}\n  \
                    Please verify the error:\n{}".format(api_request, e)
        print(error_msg)
        exit(1)



def main():
    global being_verbose
    global dry_run
    global usr
    global pwd
    global api_url
    args = parse_arguments()
    if args.verbose == True:
        being_verbose = True
    if args.dry_run == True:
        dry_run = True
    api_url = args.server_url+'/api'
    usr = args.username
    pwd = args.password
    duplicated_UID(True, False)
 
 
if __name__ == "__main__":
    main()

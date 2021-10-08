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

def program_rules_syntax(dry=True, fix=False):
    # Get all the programs
    # Check all the PR per program
    metadata = api_caller_get('programs.json?fields=id')
    programs = metadata['programs']
    for program in programs:
        # Check condition
        metadata = api_caller_get('programRules.json?fields=id,condition&filter=program.id:eq:{}'.format(program['id']))
        programRules = metadata['programRules']
        for programRule in programRules:
            payload = programRule['condition']
            response = api_caller_post('programRules/condition/description?programId={}'.format(program['id']), payload)
            # API response seems to be
            #   status OK -> Valid expression
            #   status ERROR -> Invalid expression
            if response['status'] == 'OK':
                # Expression is valid
                be_verbose("ProgramRule condition {} seems to be valid".format(payload))
            else:
                print ("ERROR: The following ProgramRule condition is wrong. Please verify!")
                print ("  Condition: {} ".format(payload))
                print ("  Hint: {}".format(response['description']))
                print ("  Please fix the program rule condition: {}/dhis-web-maintenance/index.html#/edit/programSection/programRule/{}".format(url,programRule['id']))

    # Check all the ProgramRuleActions (this works on version >2.37)
    #   some of them might contain data field, which indicates an expression that requires validation
    #    if they don't , there is no need to validate (for example they might be hidding only a field)
    metadata = api_caller_get('system/info')
    version = metadata['version'].split(".")[1].split("-")[0] # if version comes like 2.38-embargo
    if int(version) > 37:
        be_verbose("DHIS2 Version > 2.37: Performing ProgramRuleAction checks")
        metadata = api_caller_get('programRuleActions.json?fields=id,programRule[id,program[id]],data')
        programRuleActions = metadata['programRuleActions']
        for programRuleAction in programRuleActions:
            if "data" in programRuleAction:
                payload = programRuleAction['data']
                response = api_caller_post('programRuleActions/data/expression/description?programId={}'.format(metadata['program']['id']), payload)
                # API response seems to be
                #   status OK -> Valid expression
                #   status ERROR -> Invalid expression
                if response['status'] == 'OK':
                    # Expression is valid
                    be_verbose("ProgramRuleAction condition {} seems to be valid".format(payload))
                else:
                    print ("ERROR: The following ProgramRuleAction condition is wrong. Please verify!")
                    print ("  Condition: {} ".format(payload))
                    print ("  Hint: {}".format(response['description']))
                    print ("  Please fix the program rule action condition: {}/dhis-web-maintenance/index.html#/edit/programSection/programRule/{}".format(url,metadata['program']['id']))
    else:
        be_verbose("DHIS2 Version < 2.37. ProgramRuleActions check is not supported")



def duplicated_dataElements_in_sections(dry=True, fix=False):
    # List all the sections and list if any
    #  has duplicated data elements inside
    metadata = api_caller_get('sections.json?fields=id,dataElements')
    sections = metadata['sections']
    sections_with_duplicated_dataelements = []
    for section in sections:
        duplicated_dataelements = []
        unique_dataelements = []
        for dataElement in section['dataElements']:
            if dataElement['id'] in unique_dataelements:
                # Found a duplicated DE in the DataSet
                # ... this is not good!
                duplicated_dataelements.append(dataElement['id'])
            else:
                unique_dataelements.append(dataElement['id'])
        
        if len(duplicated_dataelements) > 0:
            sections_with_duplicated_dataelements.append(section['id'])
        else:
            msg = "Section: {} was inspected and no duplicated data elements were found".format(section['id'])
            be_verbose(msg)


    if len(sections_with_duplicated_dataelements) > 0:
        print ("ERROR: The following dataSets contain duplicates. Please verify!")
        print ("DataSets: {}".format(','.join(sections_with_duplicated_dataelements)))
        print ("Probably you want to execute the following call to get more information")
        print ('{}/metadata.json?filter=id:in:[{}]'
                .format(api_url,','.join(sections_with_duplicated_dataelements)))
    else:
        print ("Did not find duplicated dataelements in sections!")


def duplicated_dataElements_in_dataSets(dry=True, fix=False):
    # List all the datasets and list if any
    #  has duplicated data elements inside
    metadata = api_caller_get('dataSets.json?fields=id,dataSetElements')
    dataSets = metadata['dataSets']
    datasets_with_duplicated_dataelements = []
    for dataSet in dataSets:
        duplicated_dataelements = []
        unique_dataelements = []
        for dataElement in dataSet['dataSetElements']:
            if dataElement['dataElement']['id'] in unique_dataelements:
                # Found a duplicated DE in the DataSet
                # ... this is not good!
                duplicated_dataelements.append(dataElement['dataElement']['id'])
            else:
                unique_dataelements.append(dataElement['dataElement']['id'])
        
        if len(duplicated_dataelements) > 0:
            datasets_with_duplicated_dataelements.append(dataSet['id'])
        else:
            msg = "DataSet: {} was inspected and no duplicated data elements were found".format(dataSet['id'])
            be_verbose(msg)


    if len(datasets_with_duplicated_dataelements) > 0:
        print ("ERROR: The following dataSets contain duplicates. Please verify!")
        print ("DataSets: {}".format(','.join(datasets_with_duplicated_dataelements)))
        print ("Probably you want to execute the following call to get more information")
        print ('{}/metadata.json?filter=id:in:[{}]'
                .format(api_url,','.join(datasets_with_duplicated_dataelements)))
    else:
        print ("Did not find duplicated dataelements in datasets!")


def duplicated_categoryOptionCombos_in_categoryCombos(dry=True, fix=False):
    pass

def duplicated_categoryOptions_in_categories(dry=True, fix=False):
    # Search all categories and list if any has
    #  duplicated category options
    metadata = api_caller_get('categories.json?fields=id,categoryOptions')
    categories = metadata['categories']
    duplicated_categories = []
    for category in categories:
        # co = categoryOptions
        cos = category['categoryOptions']
        duplicated_cos = []
        unique_cos = []
        for co in cos:
            if co['id'] in unique_cos:
                # Found a duplicated categoryOption in the category
                # ... this is really BAD
                duplicated_cos.append(co['id'])
            else:
                unique_cos.append(co['id'])
        # If duplicates were found list them
        if(len(duplicated_cos) > 0):
            duplicated_categories.append(category['id'])
        else:
            msg = "Category: {} was inspected and no duplicates were found".format(category['id'])
            be_verbose(msg)
    
    if len(duplicated_categories) > 0:
        print ("ERROR: The following categories contain duplicates. Please verify!")
        print ("Categories: {}".format(','.join(duplicated_categories)))
        print ("Probably you want to execute the following call to get more information")
        print ('{}/metadata.json?filter=id:in:[{}]'
                .format(api_url,','.join(duplicated_categories)))
    else:
        print ("Did not find duplicated categoryOptions in categories!")

            

def duplicated_elements_in_all(dry=True, fix=False):
    # Verify there are no duplicates elements inside all the elements
    #  i.e. a Category imported wrongly can have the same category
    #       option several times
    #
    duplicated_categoryOptions_in_categories(dry, fix)


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
    metadata = api_caller_get('metadata.json?fields=id')
    if metadata == False:
        print ("Cannot check for duplicated_UID. Server responded badly!")
        return False

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

def api_caller_post(api_call, payload):
    # Perform an API POST call and return a dict with the content
    api_request = '{}/{}&paging=False'.format(api_url, api_call)
    be_verbose("Querying the API: "+api_request+" with payload: "+payload)

    try:
        r = requests.post(api_request, auth=(usr, pwd), data=payload)
        if r.status_code == 200:
            return json.loads(r.content)
        elif r.status_code == 404:
            print("Error 404")
            return False
        else:
            print("Error UNKNOWN")
            return False
    except Exception as e:
        error_msg = "There was a problem with the API call: \n{}\n  \
                    Please verify the error:\n{}".format(api_request, e)
        print(error_msg)
        exit(1)

def api_caller_get(api_call):
    # Perfrom an API call and return a dict with the content for valid requests
    # or false whenever there is an error with the request (code != 200)

    # Always make paging = False
    if "?" in api_call:
        api_request = '{}/{}&paging=False'.format(api_url, api_call)
    else:
        api_request = '{}/{}?paging=False'.format(api_url, api_call)

    be_verbose("Querying the API: "+api_request)

    try:
        r = requests.get(api_request, auth=(usr, pwd))
        if r.status_code == 200:
            return json.loads(r.content)
        elif r.status_code == 404:
            print("Error 404")
            return False
        else:
            print("Error UNKNOWN")
            return False
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
    global url
    args = parse_arguments()
    if args.verbose == True:
        being_verbose = True
    if args.dry_run == True:
        dry_run = True
    url = args.server_url
    api_url = args.server_url+'/api'
    usr = args.username
    pwd = args.password
    #duplicated_UID(True, False)
    #duplicated_elements_in_all(True, False)
    #duplicated_dataElements_in_dataSets(True, False)
    #duplicated_dataElements_in_sections(True, False)
    program_rules_syntax(True, False)
 
 
if __name__ == "__main__":
    main()

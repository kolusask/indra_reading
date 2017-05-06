from __future__ import absolute_import, print_function, unicode_literals
from builtins import dict, str

def get_environment():
    # Get AWS credentials
    # http://stackoverflow.com/questions/36287720/boto3-get-credentials-dynamically
    session = botocore.session.get_session()
    access_key = session.get_credentials().access_key
    secret_key = session.get_credentials().secret_key

    # Get the Elsevier keys from the Elsevier client
    environment_vars = [
            {'name': ec.api_key_env_name,
             'value': ec.elsevier_keys.get('X-ELS-APIKey')},
            {'name': ec.inst_key_env_name,
             'value': ec.elsevier_keys.get('X-ELS-Insttoken')},
            {'name': 'AWS_ACCESS_KEY_ID',
             'value': access_key},
            {'name': 'AWS_SECRET_ACCESS_KEY',
             'value': secret_key}]
    return environment_vars

if __name__ == '__main__':
    import sys
    import boto3
    import botocore.session
    from indra.literature import elsevier_client as ec

    bucket_name = 'bigmech'
    s3_client = boto3.client('s3')
    job_type =sys.argv[1]

    # Submit the reading job
    batch_client = boto3.client('batch')

    environment_vars = get_environment()

    if job_type == 'run_reach':
        basename = sys.argv[2]
        pmid_list_filename = sys.argv[3]
        main_start_ix = int(sys.argv[4])
        main_end_ix = int(sys.argv[5])
        pmid_list_key = 'reading_results/%s/pmids' % basename
        # Upload the pmid_list to Amazon S3
        s3_client.upload_file(pmid_list_filename, 'bigmech', pmid_list_key)
        pmids_per_job = 3000

        #with open(pmid_list_filename, 'rt') as f:
        #    lines = f.readlines()
        #    num_pmids = len(lines)

        # Iterate over the list of PMIDs and submit the job in chunks
        for start_ix in range(main_start_ix, main_end_ix, pmids_per_job):
            end_ix = start_ix + pmids_per_job
            if end_ix > main_end_ix:
                end_ix = main_end_ix
            job_name = '%s_%d_%d' % (basename, start_ix, end_ix)
            command_list = ['python', '-m',
                            'indra.tools.reading.run_reach_on_pmids_aws',
                            basename, '/tmp', '16', str(start_ix), str(end_ix)]
            print(command_list)
            batch_client.submit_job(jobName=job_name,
                           jobQueue='run_reach_queue',
                           jobDefinition='run_reach_jobdef',
                           containerOverrides={'environment': environment_vars,
                                               'command': command_list})
    elif job_type == 'assemble_reach':
        basename = sys.argv[2]
        job_name = '%s_assemble_reach' % basename
        command_list = ['python', '-m',
                        'indra.tools.reading.assemble_reach_stmts_aws',
                        basename]
        print(command_list)
        batch_client.submit_job(jobName=job_name, jobQueue='run_reach_queue',
                           jobDefinition='run_reach_jobdef',
                           containerOverrides={'environment': environment_vars,
                                               'command': command_list,
                                               'memory': 60000,
                                               'vcpus': 1})
    else:
        print('job type must be run_reach or assemble_reach')
        sys.exit(1)



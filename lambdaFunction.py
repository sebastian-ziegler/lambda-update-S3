from __future__ import print_function
from boto3.session import Session

import json
import urllib
import boto3
import zipfile
import tempfile
import botocore
import traceback

print('Initializing function.')

boto3.set_stream_logger(level=1)

s3 = boto3.client('s3')
codepipeline = boto3.client('codepipeline')

documentationFileName = "swagger.json"

def setup_s3_client(job_data):
    print("Initializing s3")

    key_id = job_data["artifactCredentials"]["accessKeyId"]
    key_secret = job_data["artifactCredentials"]["secretAccessKey"]
    session_token = job_data["artifactCredentials"]["sessionToken"]

    session = Session(aws_access_key_id = key_id,
       aws_secret_access_key = key_secret,
       aws_session_token = session_token)

    print("Created s3 session")

    return session.client("s3", config = botocore.client.Config(signature_version = 's3v4'))

def put_job_success(job, message):
    print('Putting job success')
    print(message)
    codepipeline.put_job_success_result(jobId = job)

def put_job_failure(job, message):
    print('Putting job failure')
    print(message)
    codepipeline.put_job_failure_result(jobId = job, failureDetails = {'message': message, 'type': 'JobFailed'})

def get_documentation(s3, artifacts):
    print("Getting documentation")
    
    doc = artifacts[0]
    objectKey = doc["location"]["s3Location"]["objectKey"]
    bucketName = doc["location"]["s3Location"]["bucketName"]

    with tempfile.NamedTemporaryFile() as tmp_file:
       print("Downloading file form s3")
       s3.download_file(bucketName, objectKey, tmp_file.name)
       with zipfile.ZipFile(tmp_file.name, 'r') as zip:
         print("Printing content on zip")
         zip.printdir()
         print(zip.namelist())
         return zip.read(documentationFileName)

def update_documentation(doc):
    print("Updating documentation")

    bucketName = "atingo-api-documentation"
    objectKey = "atingoEngineApi/api.json"
    fileName = "api.json"

    with tempfile.NamedTemporaryFile() as tmp_file:
       tmp_file.write(doc)
       s3.upload_file(tmp_file.name, bucketName, objectKey)
       tmp_file.close()

def lambda_handler(event, context):
    try:
       print(event)
       job_id = event["CodePipeline.job"]["id"]
       job_data = event["CodePipeline.job"]["data"]
       artifacts = event["CodePipeline.job"]["data"]["inputArtifacts"]
       s3 = setup_s3_client(job_data)
       docs = get_documentation(s3, artifacts)

       if (docs):
         update_documentation(docs)
         put_job_success(job_id, "Doc updated successfully")
       else:
         print("Failure")
         put_job_failure(job_id, "Doc does not exists.")

    except Exception as e:
       print('Function failed')
       print(e)
       traceback.print_exc()
       put_job_failure(job_id, 'Function exception: ' + str(e)) 

    return 'Completed!'

#some comments
import os
import requests
import json as js
import time
import logging
#make a change

logging.basicConfig(level=logging.INFO)
user_api_key = os.environ['DOMINO_USER_API_KEY']
with open('setup.py') as f:
    c = f.read()

TAG = c.partition('version=')[2].partition(',')[0]

def getOwnerId():
	logging.info('Getting ownerId')
	response = requests.get("https://"+domino_url+"/v4/users/self", auth=(user_api_key, user_api_key))
	return response.json()

def getProjectId():
    ownerId = getOwnerId().get("id")
    logging.info('Getting projectId for ownerId: '+ownerId)
    response = requests.get("https://"+domino_url+"/v4/projects?name="+project_name+"&ownerId="+ownerId, auth=(user_api_key, user_api_key))
    return response.json()

def buildModel():
    projectId = getProjectId()[0].get("id")
    logging.info('Building model for projectId: '+projectId)
    headers = {"Content-Type": "application/json", "X-Domino-Api-Key": user_api_key}
    json_data = js.dumps(
    		{
	    		"projectId": ""+projectId+"",
	    		"inferenceFunctionFile": "model_pip_pkg/model.py",
	    		"inferenceFunctionToCall": "my_model",
	    		"environmentId": None,
	    		"modelName": "My Test Model built in workshop",
	    		"logHttpRequestResponse": True,
	    		"description": "Testing default model"
    		}
		)
    response = requests.post("https://"+domino_url+"/v4/models/buildModelImage", headers = headers, data = json_data)
    return response.json()

def getModelBuildStatus(buildModelId, buildModelVersionNumber):
	logging.info('Getting build status of model '+buildModelId+' and version number '+buildModelVersionNumber)
	response = requests.get("https://"+domino_url+"/v4/models/"+str(buildModelId)+"/"+str(buildModelVersionNumber)+"/getBuildStatus", auth=(user_api_key, user_api_key))
	return response.json()

def exportModelToExternalRegistry(buildModelId, buildModelVersionNumber):
	logging.info('Exporting model '+buildModelId+' and version number '+buildModelVersionNumber +' to ECR')
	headers = {"Content-Type": "application/json", "X-Domino-Api-Key": user_api_key}
	json_data = js.dumps(
			{
				"registryUrl": "573040241134.dkr.ecr.us-west-2.amazonaws.com/",
				"repository": "model-export-demo", "tag": "churn-model",
				"username": "AWS",
				"password": ""+os.environ['ECR_PASSWORD']+""
			}
		)
	response = requests.post("https://"+domino_url+"/v4/models/"+str(buildModelId)+"/"+str(buildModelVersionNumber)+"/exportImageToRegistry", headers = headers, data = json_data)
	return response.json()

def exportModelIfBuilt(buildModelStatus):

	modelBuildIsComplete = False
	numberOfRetries = 0

	while(modelBuildIsComplete is not True):
		logging.info('number of retries: '+str(numberOfRetries)+', build model status: '+str(buildModelStatus))
		buildModelStatus = getModelBuildStatus(buildModelId, buildModelVersionNumber).get("status")
		if(buildModelStatus == "complete"):
			logging.info('Model build is complete. Exporting the model now...')
			exportModelResponse = exportModelToExternalRegistry(buildModelId, buildModelVersionNumber)
			modelBuildIsComplete = True
			break
		if(numberOfRetries == 3):
			break
		numberOfRetries += 1
		time.sleep(60) #sleep for 60 seconds before checking model build status again

	return exportModelResponse

def getExportModelStatus(exportId):
	response = requests.get("https://"+domino_url+"/v4/models/"+exportId+"/getExportImageStatus", auth=(user_api_key, user_api_key))
	return response.json()

def shareExportStatus(exportId):
	exportModelIsComplete = False
	numberOfChecks = 0

	while(exportModelIsComplete is not True):

		exportModelStatusResponse = getExportModelStatus(exportId)
		logging.info('number of checks: '+str(numberOfChecks)+', export model status: '+str(exportModelStatusResponse))
		if(exportModelStatusResponse.get("status") == "complete"):
			logging.info('Export is complete!!!')
			exportModelIsComplete = True
			break
		if(numberOfChecks == 7):
			break
		numberOfChecks += 1
		time.sleep(60) #sleep for 60 seconds before checking model export again

	return exportModelResponse


if __name__== "__main__":

	project_name = "ci-cd"
	domino_url = "test.se-team-sandbox.domino.tech"

	logging.info("Starting model build...")
	buildModelResponse = buildModel()
	buildModelId = buildModelResponse.get("modelId")
	buildModelVersionNumber = buildModelResponse.get("modelVersionId")
	logging.info("Waiting for 120 seconds before checking if model is built...")
	time.sleep(120)
	buildModelStatus = getModelBuildStatus(buildModelId, buildModelVersionNumber).get("status")
	logging.info('buildModelStatus is '+buildModelStatus)

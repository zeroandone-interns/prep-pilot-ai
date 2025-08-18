import json
import time
import boto3
import urllib
from extensions import get_logger


class TranscribeService: 
    def __init__(self):
        self.transcribe_client = boto3.client('transcribe')
        self.logger = get_logger()

    def transcribe_file(self, job_name, media_uri, media_format, language_code):
        response = self.transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': media_uri},
            MediaFormat=media_format,
            LanguageCode=language_code
        )
        self.logger.info(f"Started transcription job: {job_name}")
        max_tries = 60
        while max_tries > 0:
            max_tries -= 1
            job = self.transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_status = job['TranscriptionJob']['TranscriptionJobStatus']
            if job_status in ['COMPLETED', 'FAILED']:
                self.logger.info(f"Job {job_name} is {job_status}.")
                if job_status == 'COMPLETED':
                    response = urllib.request.urlopen(job['TranscriptionJob']['Transcript']['TranscriptFileUri'])
                    data = json.loads(response.read())
                    text = data['results']['transcripts'][0]['transcript']
                    self.logger.info("========== below is output of speech-to-text ========================")
                    self.logger.info(text)
                    self.logger.info("=====================================================================")
                return text
            elif job_status == 'FAILED':
                self.logger.error(f"Job {job_name} failed.")
                return None
            else:
                self.logger.info(f"Waiting for {job_name}. Current status is {job_status}.")
            time.sleep(10)



    
           
from census.entity.config_entity import DataIngestionConfig
from census.exception import CensusException
from census.logger import logging
from census.entity.artifact_entity import DataIngestionArtifact
import sys,os
import tarfile #To extract zip file
from six.moves import urllib #To download data
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit

class DataIngestion:

    def __init__(self, data_ingestion_config:DataIngestionConfig):
        try:
            logging.info(f"{'='*20} Data Ingestion log Started {'='*20}")
            self.data_ingestion_config = data_ingestion_config
        except Exception as e:
            raise CensusException(e,sys) from e

    def download_census_data(self) -> str:
        try:
            # To exctract download url
            download_url = self.data_ingestion_config.dataset_download_url
            #Folder location to download file    
            tgz_download_dir = self.data_ingestion_config.tgz_download_dir
            
            if os.path.exists(tgz_download_dir):
                os.remove(tgz_download_dir)

            os.makedirs(tgz_download_dir, exist_ok = True)
            tgz_file_name = os.path.basename(download_url)
            tgz_file_path = os.path.join(tgz_download_dir,tgz_file_name)
            logging.info(f"Downloading file from [{download_url}] into : [{tgz_file_path}]")
            urllib.request.urlretrieve(download_url, tgz_file_path)
            logging.info(f"file : [{tgz_file_path}] has been downloaded successfully.")
            return tgz_file_path 
        except Exception as e:
            raise CensusException(e,sys) from e

    def extrat_tgz_file(self,tgz_file_path: str):
        try:
            raw_data_dir = self.data_ingestion_config.raw_data_dir

            if os.path.exists(raw_data_dir):
                os.path.remove(raw_data_dir)

            os.makedirs(raw_data_dir,exist_ok=True)

            logging.info(f"Extracting file : [{tgz_file_path}] into : [{raw_data_dir}]")
            with tarfile.open(tgz_file_path) as census_tgz_file_obj:
                census_tgz_file_obj.extractall(path = raw_data_dir)
            logging.info(f"Extraction completed.")  
            
        except Exception as e:
            raise CensusException(e,sys) from e

    def split_data_as_train_test(self) -> DataIngestionArtifact:
        try:
            raw_data_dir = self.data_ingestion_config.raw_data_dir

            file_name = os.listdir(raw_data_dir)[0]

            census_file_path = os.path.join(raw_data_dir,file_name)

            census_data_frame = pd.read_csv(census_file_path)

            census_data_frame["income_cat"] = pd.cut(
                census_data_frame["median_income"],
                bins = [0.0,1.5,3.0,4.5,6.0,np.inf], 
                labels= [1,2,3,4,5]
            )

            strat_train_set = None
            strat_test_set = None

            split = StratifiedShuffleSplit(n_splits = 1 , test_size = 0.2, random_state = 2)

            for train_index, test_index in split.split(census_data_frame,census_data_frame["income_cat"]):
                strat_train_set = census_data_frame.loc[train_index].drop(["income_cat"], axis =1)
                strat_test_set = census_data_frame.loc[test_index].drop(["income_cat"], axis =1)

                train_file_path = os.path.join(self.data_ingestion_config.ingested_train_dir, file_name)
                test_file_path = os.path.join(self.data_ingestion_config.ingested_test_dir, file_name)
        
            if strat_train_set is not None:
                os.makedirs(self.data_ingestion_config.ingested_train_dir, exist_ok = True)
                logging.info(f"Exporting training dataset to file: [{train_file_path}]")
                strat_train_set.to_csv(train_file_path)       
        
            if strat_test_set is not None:
                os.makedirs(self.data_ingestion_config.ingested_test_dir, exist_ok = True)
                logging.info(f"Exporting test dataset to file: [{test_file_path}]")
                strat_test_set.to_csv(test_file_path)       

            data_ingestion_artifact = DataIngestionArtifact(train_file_path=train_file_path,
                                                            test_file_path=test_file_path,
                                                            is_ingested=True,
                                                            message="Data Ingestion completed sucessfully."
                                                            )
            logging.info(f"Data ingestion artifact : [{data_ingestion_artifact}]")                                                   
        except Exception as e:
            raise CensusException(e,sys) from e

            
    def initiate_data_ingestion(self) -> DataIngestionArtifact:
        try:
            tgz_file_path = self.download_census_data()
            self.extrat_tgz_file(tgz_file_path=tgz_file_path)
            return self.split_data_as_train_test()
        except Exception as e:
            raise CensusException(e,sys) from e

    def __del__(self):
        logging.info(f"{'='*20} Data Ingestion log completed {'='*20}")
            
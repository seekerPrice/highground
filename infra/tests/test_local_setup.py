"""Fake official SDK boundaries; no local/cloud resource calls."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from google.api_core.exceptions import NotFound,Forbidden
from google.cloud import bigquery

spec=importlib.util.spec_from_file_location('local_setup',Path(__file__).parents[1]/'local_setup.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)
from api.config import Settings
ENV={'FIRESTORE_EMULATOR_HOST':'127.0.0.1:8787','PUBSUB_EMULATOR_HOST':'127.0.0.1:8797','STORAGE_EMULATOR_HOST':'http://127.0.0.1:4443','BIGQUERY_EMULATOR_HOST':'http://127.0.0.1:9050'}

class LocalSetupTests(unittest.TestCase):
    def setUp(self):
        self.settings=Settings(gcp_project='test-highground',gcs_bucket='highground-media-test-highground',local_development=True,demo_mode=True)
        self.publisher=Mock();self.analytics=Mock();self.storage=Mock()
        self.analytics.project=self.storage.project=self.settings.gcp_project
        self.topic='projects/test-highground/topics/flood-events';self.dataset='test-highground.highground'
        self.publisher.topic_path.return_value=self.topic
        self.schemas=setup.validate(self.settings,ENV)
        self.resources={'topic':SimpleNamespace(name=self.topic),'bucket':SimpleNamespace(name=self.settings.gcs_bucket),'dataset':bigquery.Dataset(self.dataset)}
        self.tables={name:bigquery.Table(self.dataset+'.'+name,schema=fields) for name,fields in self.schemas.items()}
        def get(kind):
            if kind not in self.resources:raise NotFound('absent')
            return self.resources[kind]
        self.publisher.get_topic.side_effect=lambda **kwargs:get('topic')
        self.storage.get_bucket.side_effect=lambda *args,**kwargs:get('bucket')
        self.analytics.get_dataset.side_effect=lambda *args,**kwargs:get('dataset')
        def get_table(identity,**kwargs):
            name=identity.rsplit('.',1)[1]
            if name not in self.tables:raise NotFound('absent')
            return self.tables[name]
        self.analytics.get_table.side_effect=get_table
        self.publisher.create_topic.side_effect=lambda **kwargs:self.resources.update(topic=SimpleNamespace(name=kwargs['request']['name']))
        self.storage.create_bucket.side_effect=lambda name,**kwargs:self.resources.update(bucket=SimpleNamespace(name=name))
        self.analytics.create_dataset.side_effect=lambda dataset,**kwargs:self.resources.update(dataset=dataset)
        self.analytics.create_table.side_effect=lambda table,**kwargs:self.tables.update({table.table_id:table})

    def run_setup(self,apply=False,env=None):
        with patch.dict(setup.os.environ,ENV if env is None else env,clear=True),patch.object(setup,'create_analytics_client',return_value=self.analytics) as analytics_factory,patch.object(setup,'create_storage_client',return_value=self.storage) as storage_factory,patch.object(setup.pubsub_v1,'PublisherClient',return_value=self.publisher) as publisher_factory:
            return setup.initialize(self.settings,apply=apply)

    def no_creates(self):
        for client,method in [(self.publisher,'create_topic'),(self.storage,'create_bucket'),(self.analytics,'create_dataset'),(self.analytics,'create_table')]:getattr(client,method).assert_not_called()

    def test_missing_endpoint_cannot_construct_any_client(self):
        env=dict(ENV);env.pop('STORAGE_EMULATOR_HOST')
        with patch.dict(setup.os.environ,env,clear=True),patch.object(setup,'create_analytics_client') as analytics,patch.object(setup,'create_storage_client') as storage,patch.object(setup.pubsub_v1,'PublisherClient') as publisher:
            with self.assertRaises(ValueError):setup.initialize(self.settings,apply=True)
            analytics.assert_not_called();storage.assert_not_called();publisher.assert_not_called()

    def test_existing_compatible_resources_create_nothing(self):
        self.assertEqual(self.run_setup(True),{'mode':'apply','missing_resources':0,'verified':True})
        self.no_creates();self.assertEqual(self.analytics.get_table.call_count,10)
        self.analytics.close.assert_called_once();self.storage.close.assert_called_once();self.publisher.stop.assert_called_once()

    def test_dryrun_missing_resources_is_readonly(self):
        self.resources.clear();self.tables.clear()
        result=self.run_setup();self.assertEqual(result['missing_resources'],8);self.no_creates()

    def test_absent_resources_created_only_at_configured_ids_and_verified(self):
        self.resources.clear();self.tables.clear();self.assertTrue(self.run_setup(True)['verified'])
        self.publisher.create_topic.assert_called_once_with(request={'name':self.topic},timeout=10,retry=None)
        self.storage.create_bucket.assert_called_once_with(self.settings.gcs_bucket,timeout=10,retry=None)
        self.assertEqual(self.analytics.create_table.call_count,5)
        self.assertTrue(all(call.args[0].project==self.settings.gcp_project and call.args[0].dataset_id=='highground' for call in self.analytics.create_table.call_args_list))
        self.assertEqual(set(self.tables),set(setup.TABLES))

    def test_permission_failure_is_never_absence_and_all_clients_close(self):
        primary=Forbidden('private SDK body');self.analytics.get_table.side_effect=primary
        self.publisher.stop.side_effect=RuntimeError('sdk private close detail')
        with self.assertRaises(Forbidden) as caught:self.run_setup(True)
        self.assertIs(caught.exception,primary);self.no_creates()
        self.analytics.close.assert_called_once();self.storage.close.assert_called_once();self.publisher.stop.assert_called_once()
        self.assertNotIn('sdk private close detail',primary.__notes__[0])

    def test_schema_mismatch_fails_before_any_dependent_creation(self):
        self.resources.pop('topic');self.tables['outcomes']=bigquery.Table(self.dataset+'.outcomes',schema=[bigquery.SchemaField('wrong','STRING')])
        with self.assertRaises(ValueError):self.run_setup(True)
        self.no_creates();self.analytics.delete_dataset.assert_not_called();self.analytics.delete_table.assert_not_called()

if __name__=='__main__':unittest.main()

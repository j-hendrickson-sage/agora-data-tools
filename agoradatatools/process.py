import agoradatatools.etl.extract as extract
import agoradatatools.etl.transform as transform
import agoradatatools.etl.load as load
import agoradatatools.etl.utils as utils
import sys
from pandas import DataFrame

def process_dataset(dataset_obj: dict, syn=None):
    """
    Takes in a dataset from the configuration file and passes it through the
    ETL process
    """

    print(dataset_obj)
    dataset_name = list(dataset_obj)[0]
    entities_as_df = {}

    for entity in dataset_obj[dataset_name]['files']:
        entity_id = list(entity.keys())[0]
        entity_format = list(entity.values())[0]

        df = extract.get_entity_as_df(syn_id=entity_id, format=entity_format, syn=syn)
        df = transform.standardize_column_names(df=df)
        df = transform.standardize_values(df=df)

        # the column rename gets applied to all entities in a dataset
        if "column_rename" in dataset_obj[dataset_name].keys():
            df = transform.rename_columns(df=df, column_map=dataset_obj[dataset_name]['column_rename'])

        entities_as_df[entity_id] = df

    if "custom_transformations" in dataset_obj[dataset_name].keys():
        df = transform.apply_custom_transformations(datasets=entities_as_df, dataset_name=dataset_name)
    else:
        df = entities_as_df[list(entities_as_df)[0]]


    try:
        # sys.exit()
        json_path = load.df_to_json(df=df, filename=dataset_name + "." + dataset_obj[dataset_name]['final_format'])
        syn_obj = load.load(file_path=json_path, provenance=dataset_obj[dataset_name]['provenance'],
                            destination=dataset_obj[dataset_name]['destination'],
                            syn=syn)
    except Exception as load_error:
        print("There was an error loading " + dataset_name)
        print(load_error)
        return

    return syn_obj


# def process_single_file(dataset_obj: dict, syn=None):
#     """
#     Puts a single file through the entire ETL process.
#     If process is successful, it will return a string
#     with the Synapse id of the newly loaded file
#     :param dataset_obj: a file object from the configuration
#     :return: a Synapse id
#     """
#
#     # individual exceptions are defined in each file
#     try:
#         df = extract.get_entity_as_df(syn_id=dataset_obj['id'], format=dataset_obj['format'], syn=syn)
#     except Exception as extract_error:
#         print("There was an error extracting " + dataset_obj['id'])
#         print(extract_error)
#         return
#
#     try:
#         df = transform.standardize_column_names(df=df)
#         df = transform.standardize_values(df=df)
#     except Exception as transform_error:
#         print("There was an error transforming " + dataset_obj['id'])
#         print(transform_error)
#         return
#
#     if "column_rename" in dataset_obj.keys():
#         df = transform.rename_columns(df=df, column_map=dataset_obj['column_rename'])
#
#     if "additional_transformations" in dataset_obj.keys():
#         df = transform.apply_additional_transformations(df=df, file_obj=dataset_obj)
#
#     try:
#         json_path = load.df_to_json(df=df, filename=dataset_obj['final_filename'])
#         syn_obj = load.load(file_path=json_path, provenance=dataset_obj['provenance'], destination=dataset_obj['destination'],
#                             syn=syn)
#     except Exception as load_error:
#         print("There was an error loading " + dataset_obj['id'])
#         print(load_error)
#         return
#
#     print(syn_obj)
#     return syn_obj


def create_data_manifest(manifest: list[tuple]) -> DataFrame:
    return DataFrame(manifest, columns=['id', 'version'])


def process_all_files(config_path: str = None):
    """
    This function will run read through the entire configuration
    and process each file.
    :param config_path: the path to the configuration file
    """

    syn = utils._login_to_synapse()
    manifest = []

    if config_path:
        config = utils._get_config(config_path=config_path)
    else:
        config = utils._get_config()

    datasets = config[1]['datasets']

    # create staging location
    load.create_temp_location()

    for dataset in datasets:
        new_syn_tuple = process_dataset(dataset_obj=dataset, syn=syn)
        manifest.append(new_syn_tuple)

    # create manifest
    manifest_df = create_data_manifest(manifest=manifest)
    manifest_path = load.df_to_csv(df=manifest_df, filename="data_manifest.csv")

    load.load(file_path=manifest_path, provenance=manifest_df['id'].to_list(), destination=config[0]['destination'])

def main():
    process_all_files(config_path=sys.argv[1])

if __name__ == "__main__":
    main()
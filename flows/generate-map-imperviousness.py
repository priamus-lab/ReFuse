from prefect import Flow, Parameter, task, mapped, unmapped
from prefect.core.parameter import DateTimeParameter
from prefect.executors import LocalExecutor
from refuse.sentinel2collection import search_sentinel2, download_sentinel2

FLOW_NAME = "test-flow"
PROJECT_NAME = "imperviousness"

@task(log_stdout=True)
def search(area_of_interest, start_date, end_date, cloud_coverage_tresh, frequency):
    print(f"Area of Interest: {area_of_interest}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")

    search_result = search_sentinel2(
            area_of_interest=area_of_interest,
            start_date=start_date,
            end_date=end_date,
            cloud_coverage_tresh=cloud_coverage_tresh,
            collection="sentinel-s2-l2a-cogs",
            frequency=frequency)

    return search_result


@task(log_stdout=True)
def download(area_of_interest, start_date, end_date, search_result, destination_path):
    print(f"Downloading search result: {search_result}")

    return download_sentinel2(area_of_interest=area_of_interest,
                              start_date=start_date,
                              end_date=end_date,
                              search_result=search_result,
                              destination_path=destination_path)


@task(log_stdout=True)
def patches_extraction(raster_path):
    # TODO
    pass


@task(log_stdout=True)
def predict(patch, input_raster_path):
    # TODO
    pass


@task(log_stdout=True)
def store_data(prediction_filepath):
    # TODO
    pass


with Flow(FLOW_NAME) as flow:
    area_of_interest = Parameter("area_of_interest")
    start_date = DateTimeParameter("start_date")
    end_date = DateTimeParameter("end_date")
    destination_path = Parameter("destination_path")
    cloud_coverage_tresh = Parameter("cloud_coverage_tresh", required=False)
    frequency = Parameter("frequency", required=False)

    search_results = search(area_of_interest=area_of_interest,
                            start_date=start_date,
                            end_date=end_date,
                            cloud_coverage_tresh=cloud_coverage_tresh,
                            frequency=frequency)

    path_downloaded_files = download.map(area_of_interest=unmapped(area_of_interest),
                                         start_date=unmapped(start_date),
                                         end_date=unmapped(end_date),
                                         search_result=mapped(search_results),
                                         destination_path=unmapped(destination_path))

    patches_list = patches_extraction(raster_path=path_downloaded_files)

    prediction_filepath = predict.map(patch=patches_list,
                                      input_raster_path=unmapped(path_downloaded_files))

    path_prediction_raster = store_data(prediction_filepath)


if __name__ == "__main__":
    # Register the flow
    flow_id = flow.register(project_name=PROJECT_NAME, idempotency_key=flow.serialized_hash())
    print(f"flow_id: {flow_id}")

    # parameters = {
    #     "area_of_interest": "Polygon ((14.1450181130888577 40.84125510887623278, 14.1450181130888577 40.85350293558663992, 14.16681872234173234 40.85350293558663992, 14.16681872234173234 40.84125510887623278, 14.1450181130888577 40.84125510887623278))",
    #     "start_date": "2020-06-14",
    #     "end_date": "2022-06-14",
    #     "destination_path": "s3://my-bucket-test/test1"
    # }
    # flow.run(parameters=parameters, executor=LocalExecutor())


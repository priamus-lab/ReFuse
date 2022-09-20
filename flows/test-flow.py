from prefect import Flow, Parameter, task, mapped
from prefect.core.parameter import DateTimeParameter
from prefect.executors import LocalExecutor

FLOW_NAME = "test-flow"


@task(log_stdout=True)
def search(area_of_interest, start_date, end_date):
    print(f"Area of Interest: {area_of_interest}")
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")

    return ["2020-05-01", "2020-05-10"]


@task(log_stdout=True)
def download(catalog_date):
    print(f"Downloading catalog for the date: {catalog_date}")


with Flow(FLOW_NAME) as flow:
    area_of_interest = Parameter("area_of_interest")
    start_date = DateTimeParameter("start_date")
    end_date = DateTimeParameter("end_date")
    cloud_coverage_tresh = Parameter("cloud_coverage_tresh", required=False)
    frequency = Parameter("frequency", required=False)

    list_available_dates = search(area_of_interest=area_of_interest,
                                  start_date=start_date,
                                  end_date=end_date)

    path_downloaded_files = download.map(catalog_date=mapped(list_available_dates))


if __name__ == "__main__":
    parameters = {
        "area_of_interest": "jsafhjkdfshisdfk",
        "start_date": "2022-05-08",
        "end_date": "2022-05-10",
    }
    flow.run(parameters=parameters, executor=LocalExecutor())


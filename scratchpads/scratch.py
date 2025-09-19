import marimo

__generated_with = "0.14.17"
app = marimo.App(width="full")


@app.cell
async def _():
    from libsms import Client
    from libsms.models import MyDataModel
    from libsms.api.my_tag import get_my_data_model
    from libsms.types import Response

    client = Client(base_url="https://api.example.com")

    async with client as client:
        my_data: MyDataModel = await get_my_data_model.asyncio(client=client)
        response: Response[MyDataModel] = await get_my_data_model.asyncio_detailed(client=client)
    return


if __name__ == "__main__":
    app.run()

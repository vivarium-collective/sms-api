# @pytest.mark.asyncio
# async def test_run_analysis(request, database_service: DatabaseService) -> None:
#     transport = ASGITransport(app=app)
#     async with AsyncClient(transport=transport, base_url="http://testserver") as client:
#         response = await client.post("/experiments", json=request.model_dump())
#         response.raise_for_status()
#         data = response.json()
#         assert isinstance(data["config"]["analysis_options"]["experiment_id"], list)

# TODO: recreate the same config mechanism from analyses to experiments!

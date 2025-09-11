import marimo

__generated_with = "0.14.16"
app = marimo.App(width="full")


@app.cell
def _():
    return


@app.function
def test_variant_dtos():
    from sms_api.simulation.models import Variant, VariantConfig, VariantParameter, VariantOpType

    vparam1 = VariantParameter(name="method", value=["multiplicative"])
    vparam2 = VariantParameter(name="noise", value=[0.1])
    vparam3 = VariantParameter(name="condition", value=["basal", "with_aa", "acetate", "succinate", "no_oxygen"])
    vparam4 = VariantParameter(
        name="xyz",
        value=[
            0.1,
            0.10952380952380952,
            0.11904761904761905,
        ],
    )
    variant_a = Variant(module_name="perturb_growth_param", parameters=[vparam1, vparam2], op=VariantOpType.CARTESIAN)
    variant_b = Variant(module_name="condition", parameters=[vparam3, vparam4])
    variant_config = VariantConfig(variants=[variant_a, variant_b])
    assert list(variant_config.to_dict().keys()) == ["perturb_growth_param", "condition"]
    print(variant_config)


@app.cell
def _():
    test_variant_dtos()
    return


@app.cell
def _():
    from sms_api.simulation.models import Variant, VariantConfig, VariantParameter, VariantOpType, SimulationConfig

    return (SimulationConfig,)


@app.cell
def _(SimulationConfig):
    config = SimulationConfig.from_base()
    return (config,)


@app.cell
def _(config):
    config.emitter_arg
    return


@app.cell
def _(config):
    config.experiment_id
    return


@app.cell
def _(config):
    config.model_dump()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

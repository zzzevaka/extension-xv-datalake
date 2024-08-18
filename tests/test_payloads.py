from datetime import datetime

import pytest

from connect_ext_datalake.services.payloads import prepare_ff_request_data, prepare_tcr_data


expected_format = "%Y-%m-%dT%H:%M:%S%z"


def test_ff_request_mapping(ff_request):
    ff_payload = prepare_ff_request_data(ff_request, 'TEST')
    assert ff_payload['table_name'] == 'cmp_connect_fulfillmentrequest'
    assert ff_payload['update_type'] == 'update'

    assert ff_payload['fulfillment_request']['id'] == ff_request['id']
    assert (
        ff_payload['fulfillment_request']['name']
        == f"Fulfillment request for asset {ff_request['asset']['id']}."
    )
    assert ff_payload['fulfillment_request']['asset_id'] == ff_request['asset']['id']
    assert ff_payload['fulfillment_request']['product_id'] == ff_request['asset']['product']['id']
    assert (
        ff_payload['fulfillment_request']['asset_external_id'] == ff_request['asset']['external_id']
    )
    assert (
        ff_payload['fulfillment_request']['asset_external_uid']
        == ff_request['asset']['external_uid']
    )
    assert ff_payload['fulfillment_request']['activation_link'] == ff_request['params_form_url']
    assert ff_payload['fulfillment_request']['hub_cd'] == 'TEST'
    try:
        parsed_date = datetime.strptime(
            ff_payload['fulfillment_request']['published_at'], expected_format
        )
        assert parsed_date is not None
    except ValueError:
        pytest.fail(
            f"Date string '{date_string}' does not match the expected format '{expected_format}'"
        )


def test_tcr_mapping(tcr_request):
    tcr_payload = prepare_tcr_data(tcr_request, 'TEST')
    assert tcr_payload['table_name'] == 'cmp_connect_tierconfigrequest'
    assert tcr_payload['update_type'] == 'new'

    assert tcr_payload['tier_config_request']['id'] == tcr_request['id']
    assert (
        tcr_payload['tier_config_request']['name']
        == f"Tier Configuration Request for {tcr_request['configuration']['account']['id']}."
    )
    assert (
        tcr_payload['tier_config_request']['tier_account_id']
        == tcr_request['configuration']['account']['id']
    )
    assert (
        tcr_payload['tier_config_request']['product_id']
        == tcr_request['configuration']['product']['id']
    )
    assert (
        tcr_payload['tier_config_request']['activation_link'] == tcr_request['activation']['link']
    )
    assert (
        tcr_payload['tier_config_request']['tier_level']
        == tcr_request['configuration']['tier_level']
    )
    assert tcr_payload['tier_config_request']['hub_cd'] == 'TEST'
    try:
        parsed_date = datetime.strptime(
            tcr_payload['tier_config_request']['published_at'], expected_format
        )
        assert parsed_date is not None
    except ValueError:
        pytest.fail(
            f"Date string '{date_string}' does not match the expected format '{expected_format}'"
        )

# -*- coding: utf-8 -*-
#
# Copyright (c) 2023, Ingram Micro - Rahul Mondal
# All rights reserved.
#
from connect.client import ConnectClient, R

from connect_ext_datalake.schemas import Product, PublishProductResponse, Settings
from connect_ext_datalake.client import GooglePubsubClient


def get_pubsub_client(installation):
    client = GooglePubsubClient(
        Settings(
            account_info=installation['settings'].get('account_info', {}),
            product_topic=installation['settings'].get('product_topic', ''),
        ),
    )

    client.validate()

    return client


def remove_properties(dict: dict, properties: list):
    for prop in properties:
        if prop in dict.keys():
            dict.pop(prop)


def sanitize_product(product: dict):
    remove_properties(
        product,
        [
            'changes_description',
            'public',
            'events',
            'configurations',
            'usage_rule',
            'stats',
            'extensions',
        ],
    )

    return product


def sanitize_parameters(parameters: list):
    for parameter in parameters:
        remove_properties(
            parameter,
            ['events'],
        )

    return parameters


def prepare_product_data_from_listing_request(client, listing_request):
    product_id = listing_request['product']['id']

    data = {
        'update_type': listing_request['type'],
        'product': listing_request['product'],
    }

    if listing_request['type'] != 'remove':
        data['product'] = sanitize_product(client.products[product_id].get())
        data['product']['parameters'] = sanitize_parameters(
            list(client.products[product_id].parameters.all()),
        )

    return data


def prepare_product_data_from_product(client, product):
    product_id = product['id']

    data = {
        'update_type': 'update',
        'product': sanitize_product(product),
    }

    data['product']['parameters'] = sanitize_parameters(
        list(client.products[product_id].parameters.all()),
    )

    return data


def publish_products(
    client: ConnectClient,
    products: list[Product],
    installation,
):
    response = []
    pubsub_client = get_pubsub_client(installation)
    product_ids = [product.id for product in products]

    connect_products = client.products.filter(id__in=product_ids)

    for connect_product in connect_products:
        product_response = PublishProductResponse(id=connect_product['id'])
        response.append(product_response)
        try:
            payload = prepare_product_data_from_product(client, connect_product)
            pubsub_client.publish(payload)

            product_response.published = True
        except Exception as e:
            product_response.published = False
            product_response.error = f'{type(e).__name__} : {str(e)}'

    return response


def list_products(client: ConnectClient):
    connect_products = client.products.filter(
        R().visibility.listing.eq(True) or R().visibility.syndication.eq(True),
    ).all()

    return list(map(Product.parse_obj, connect_products))

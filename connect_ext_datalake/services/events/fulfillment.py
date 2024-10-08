from connect.client import ClientError, R
from connect.eaas.core.decorators import event, schedulable, variables
from connect.eaas.core.responses import BackgroundResponse, ScheduledExecutionResponse

from connect_ext_datalake.services.client import GooglePubsubClient
from connect_ext_datalake.services.publish import publish_ff_request
from connect_ext_datalake.services.settings import get_settings, validate_hub_cd


class FulfillmentEventsMixin:
    def __process_ff_request_event(self, ff_request):
        return BackgroundResponse.done()

        self.logger.info(f"Obtained fulfillment request with id {ff_request['id']}")
        hub_id = ff_request.get('asset', {}).get('connection', {}).get('hub', {}).get('id', None)
        if hub_id:
            setting = get_settings(self.installation, hub_id)
            if setting:
                validate_hub_cd(setting.hub.hub_cd, hub_id)
                try:
                    client = GooglePubsubClient(setting)
                    publish_ff_request(
                        client,
                        ff_request,
                        self.logger,
                        setting.hub.hub_cd,
                    )
                except Exception as e:
                    self.logger.exception(
                        f"Publish of fulfillment request {ff_request['id']} is failed."
                    )
                    raise e
            else:
                self.logger.info(
                    f"Publish of fulfillment request {ff_request['id']} is not processed"
                    f" as settings not available for respective hub {hub_id}."
                )
        else:
            self.logger.info(
                f"Publish of fulfillment request {ff_request['id']} is not processed"
                f" as hub id is not found in request."
            )
        return BackgroundResponse.done()

    @event(
        'asset_suspend_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'scheduled',
            'revoking',
            'revoked',
        ],
    )
    def handle_asset_suspend_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'asset_adjustment_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'inquiring',
            'scheduled',
            'revoking',
            'revoked',
            'tiers_setup',
        ],
    )
    def handle_asset_adjustment_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'asset_cancel_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'scheduled',
            'revoking',
            'revoked',
        ],
    )
    def handle_asset_cancel_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'tier_account_update_request_processing',
        statuses=[
            'pending',
            'accepted',
            'ignored',
        ],
    )
    def handle_tier_account_update_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'asset_purchase_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'inquiring',
            'scheduled',
            'revoking',
            'revoked',
            'tiers_setup',
        ],
    )
    def handle_asset_purchase_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'asset_change_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'inquiring',
            'scheduled',
            'revoking',
            'revoked',
            'tiers_setup',
        ],
    )
    def handle_asset_change_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)

    @event(
        'asset_resume_request_processing',
        statuses=[
            'pending',
            'approved',
            'failed',
            'scheduled',
            'revoking',
            'revoked',
        ],
    )
    def handle_asset_resume_request_processing(self, ff_request):
        return self.__process_ff_request_event(ff_request)


@variables(
    [
        {
            'name': 'FF_REQUEST_PAGE_SIZE',
            'initial_value': '100',
        },
    ],
)
class FulfillmentTasksMixin:
    @schedulable(
        'Publish FF Requests',
        'Publish FF Requests to Xvantage Goggle PubSub Topic. "asset_ids" and "installation_id" '
        'should be specified',
    )
    def publish_ff_requests(
        self,
        schedule,
    ):
        self.logger.info(
            f"Start of execution for schedule {schedule['id']} " f'for publishing ff requests'
        )
        installation_id = schedule['parameter'].get('installation_id')
        asset_ids = schedule['parameter'].get('asset_ids')
        statuses = schedule['parameter'].get('statuses')
        if installation_id is None:
            return ScheduledExecutionResponse.fail('Installation_id should be specified')

        client = self.get_installation_admin_client(installation_id)
        client.resourceset_append = False
        installation = client('devops').installations[installation_id].get()

        try:
            ff_request_qs = (
                client.requests.all()
                .order_by('created')
                .limit(int(self.config['FF_REQUEST_PAGE_SIZE']))
            )
            if asset_ids:
                ff_request_qs = ff_request_qs.filter(R().asset__id.in_(asset_ids))
            if statuses:
                ff_request_qs = ff_request_qs.filter(R().status.in_(statuses))
            else:
                ff_request_qs = ff_request_qs.filter(
                    R().status.in_(
                        [
                            'tiers_setup',
                            'inquiring',
                            'pending',
                            'approved',
                            'failed',
                            'draft',
                            'scheduled',
                            'revoking',
                            'revoked',
                        ]
                    )
                )

            self.logger.info(f'Total number of FF requests is: {ff_request_qs.count()}')
            counter = 1

            for ff_request in ff_request_qs:
                hub_id = ff_request['asset']['connection']['hub']['id']
                setting = get_settings(installation, hub_id)
                if setting:
                    validate_hub_cd(setting.hub.hub_cd, hub_id)
                    pubsub_client = GooglePubsubClient(setting)
                    self.logger.info(f'Processing FF request in {counter} position')
                    publish_ff_request(pubsub_client, ff_request, self.logger, setting.hub.hub_cd)
                else:
                    self.logger.info(
                        f"Publish of FF request {ff_request['id']} is not processed"
                        f" as settings not available for respective hub."
                    )
                counter += 1
        except ClientError as e:
            self.logger.exception('Problem in calling Connect or Google APIs.')
            raise e

        return ScheduledExecutionResponse.done()

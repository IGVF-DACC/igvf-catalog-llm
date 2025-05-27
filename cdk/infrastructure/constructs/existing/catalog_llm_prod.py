from constructs import Construct
from typing import Any
import aws_cdk as cdk
from aws_cdk.aws_certificatemanager import Certificate
from aws_cdk.aws_route53 import HostedZone
from aws_cdk.aws_ec2 import Vpc
from aws_cdk.aws_events import EventBus
from aws_cdk.aws_chatbot import SlackChannelConfiguration
from aws_cdk.aws_secretsmanager import Secret
from aws_cdk.aws_sns import Topic


class Resources(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.network = Network(
            self,
            'Network',
        )
        self.domain = Domain(
            self,
            'Domain',
        )
        self.code_star_connection = CodeStarConnection(
            self,
            'CodeStarConnection',
        )
        self.notification = Notification(
            self,
            'Notification',
        )
        self.bus = Bus(
            self,
            'Bus',
        )
        self.docker_hub_credentials = DockerHubCredentials(
            self,
            'DockerHubCredentials',
        )

US_WEST_2 = cdk.Environment(
    account='636503752262',
    region='us-west-2'
)

class Domain(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.name = 'demo.igvf.org'
        self.certificate = Certificate.from_certificate_arn(
            self,
            'DomainCertificate',
            'arn:aws:acm:us-west-2:109189702753:certificate/6bee1171-2028-43eb-aab8-d992da3c60df'
        )
        self.zone = HostedZone.from_lookup(
            self,
            'DomainZone',
            domain_name=self.name,
        )


class Network(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.vpc = Vpc.from_lookup(
            self,
            'Vpc',
            vpc_id='vpc-0c07b4924c61a6b78'
        )

class Bus(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.default = EventBus.from_event_bus_arn(
            self,
            'DefaultBus',
            'arn:aws:events:us-west-2:636503752262:event-bus/default',
        )

class Notification(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.encode_dcc_chatbot = SlackChannelConfiguration.from_slack_channel_configuration_arn(
            self,
            'EncodeDCCChatbot',
            'arn:aws:chatbot::636503752262:chat-configuration/slack-channel/slack-catalog'

        )
        self.alarm_notification_topic = Topic.from_topic_arn(
            self,
            'AlarmNotificationTopic',
            topic_arn='arn:aws:sns:us-west-2:636503752262:IGVFProdCatalogSlack'
        )

class CodeStarConnection(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.arn = (
            'arn:aws:codestar-connections:'
            'us-west-2:636503752262:'
            'connection/fe8ba008-c9f7-4076-83bb-2c57ba0ecd45'
        )

class DockerHubCredentials(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.secret = Secret.from_secret_complete_arn(
            self,
            'DockerSecret',
            'arn:aws:secretsmanager:us-west-2:636503752262:secret:docker-hub-credentials-lfFj2J',
        )


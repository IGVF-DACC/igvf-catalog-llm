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
            'DemoNetwork',
        )
        self.domain = Domain(
            self,
            'DemoDomain',
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
    account='109189702753',
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
            vpc_id='vpc-0a5f4ff3233b1b79b'
        )

class Bus(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.default = EventBus.from_event_bus_arn(
            self,
            'DefaultBus',
            'arn:aws:events:us-west-2:109189702753:event-bus/default',
        )

class Notification(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.encode_dcc_chatbot = SlackChannelConfiguration.from_slack_channel_configuration_arn(
            self,
            'EncodeDCCChatbot',
            'arn:aws:chatbot::109189702753:chat-configuration/slack-channel/aws-chatbot'
        )
        self.alarm_notification_topic = Topic.from_topic_arn(
            self,
            'AlarmNotificationTopic',
            topic_arn='arn:aws:sns:us-west-2:109189702753:NotificationStack-AlarmNotificationTopic58BFACC9-i80Mhdn4q9BN'
        )

class CodeStarConnection(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.arn = (
            'arn:aws:codestar-connections:'
            'us-west-2:109189702753:'
            'connection/d65802e7-37d9-4be6-bc86-f94b2104b5ff'
        )

class DockerHubCredentials(Construct):
    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.secret = Secret.from_secret_complete_arn(
            self,
            'DockerSecret',
            'arn:aws:secretsmanager:us-west-2:109189702753:secret:docker-hub-credentials-EStRH5',
        )


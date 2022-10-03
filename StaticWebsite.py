# abdulnaser sheikh
# Oct 03, 2022
# deploy your react static website on aws

from asyncio import protocols
from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_ssm as ssm,
    aws_route53 as route53,
    aws_route53_targets as targets,
    aws_s3_deployment as s3deploy,
    aws_certificatemanager as acm,
    aws_iam as iam,
)
import aws_cdk as cdk
from constructs import Construct
import aws_cdk.aws_route53_targets as targets

account_num = ""
region=""
hosted_zone_id=''
WEB_APP_DOMAIN = ""
BCUKET_NAME = WEB_APP_DOMAIN.split(".")[0]
env_US = cdk.Environment(account=account_num, region=region)


class AbdulnsheikhStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs, env=env_US) 

        # Create a public bucket (WEB_APP_DOMAIN)
        self.s3_bucket_public = s3.Bucket(
            self, f"{BCUKET_NAME}PublicBucket",
            # Bucket name must be globally unique.
            # If not set it's assigned by Cloudformation
            bucket_name="www." + WEB_APP_DOMAIN,
            removal_policy=RemovalPolicy.DESTROY,  # Delete objects on bucket removal
            auto_delete_objects=True, 
            access_control=s3.BucketAccessControl.PUBLIC_READ, 
            website_error_document='index.html', 
            website_index_document='index.html'
        )

        # deploy the built react folder
        s3deploy.BucketDeployment(self, "DeployWebsite",
                                  sources=[s3deploy.Source.asset(
                                      "./app/abdulnsheikh/build/")],<--- change abdulnsheikh to whatever project name in react
                                  destination_bucket=self.s3_bucket_public,
                                  destination_key_prefix=""
                                  )

        # Create a private bucket (WEB_APP_DOMAIN)
        self.s3_bucket_private = s3.Bucket(
            self, f"{BCUKET_NAME}PrivateBucket",
            # Bucket name must be globally unique.
            # If not set it's assigned by Cloudformation
            bucket_name=WEB_APP_DOMAIN,
            removal_policy=RemovalPolicy.DESTROY,  # Delete objects on bucket removal
            auto_delete_objects=True,
            access_control=s3.BucketAccessControl.PRIVATE,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, 
            website_redirect=s3.RedirectTarget(
                host_name="www." + WEB_APP_DOMAIN,
                protocol=s3.RedirectProtocol.HTTP, 
                ), 
        )

        zone = route53.PublicHostedZone.from_hosted_zone_attributes(
            self, "HostedZone", zone_name=WEB_APP_DOMAIN, hosted_zone_id=hosted_zone_id)

        # ***** https certificates
        www_acm = acm.Certificate(self, "www_acm_Certificate",
                                  domain_name="www." + WEB_APP_DOMAIN,
                                  validation=acm.CertificateValidation.from_dns(
                                      zone)
                                  )
        none_www_acm = acm.Certificate(self, "none_www_acm_Certificate",
                                  domain_name=WEB_APP_DOMAIN,
                                  validation=acm.CertificateValidation.from_dns(
                                      zone)
                                  )

        # cloudfront error response
        error_response = [
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(amount=0),
                    response_http_status=200,
                )
            ]

        # Create the cloudfront distribution
        self.cloudfront_distro_public = cloudfront.Distribution(
            self, 'cdndistribution_public',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.s3_bucket_public),  
            ),
            domain_names=['www.' + WEB_APP_DOMAIN],
            certificate=www_acm,
            error_responses=error_response
        )
        
        self.cloudfront_distro_private = cloudfront.Distribution(
            self, 'cdndistribution_private',
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.s3_bucket_public),  
            ),
            domain_names=[WEB_APP_DOMAIN],
            certificate=none_www_acm,
            error_responses=error_response
        )
 
        # ***** A records
        www_a_record = route53.ARecord(
            self,
            id="WWWAliasRecord",
            zone=zone,
            record_name="www",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.cloudfront_distro_public))
        )

        www_a_record = route53.ARecord(
            self,
            id="AliasRecord",
            zone=zone,
            record_name="",
            target=route53.RecordTarget.from_alias(
                targets.CloudFrontTarget(self.cloudfront_distro_private))
        )

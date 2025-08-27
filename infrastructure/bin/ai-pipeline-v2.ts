#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { AIPipelineV2Stack } from '../lib/ai-pipeline-v2-stack';

const app = new cdk.App();

// Get environment context
const environment = app.node.tryGetContext('environment') || 'dev';
const account = process.env.CDK_DEFAULT_ACCOUNT;
const region = process.env.CDK_DEFAULT_REGION || 'us-east-1';

// Create the main stack
new AIPipelineV2Stack(app, `AIPipelineV2Stack-${environment}`, {
  env: {
    account: account,
    region: region,
  },
  environment: environment,
  tags: {
    Project: 'AI-Pipeline-Orchestrator-V2',
    Environment: environment,
    ManagedBy: 'CDK'
  }
});
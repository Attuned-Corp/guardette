resource "aws_lambda_function" "lambda_model_function" {
  function_name = "${var.name}-lambda"
  role          = aws_iam_role.lambda_model_role.arn

  image_uri    = var.image_uri
  package_type = "Image"
  memory_size  = 256
  # Set the timeout to 60 seconds
  timeout       = 60
  architectures = [var.image_architecture]

  environment {
    variables = var.environment_vars
  }
}

data "aws_iam_policy_document" "lambda_model_role" {
  statement {
    sid     = ""
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_iam_role" "lambda_model_role" {
  name               = "${var.name}-lambda-model-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_model_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_model_policy_attachement" {
  role       = aws_iam_role.lambda_model_role.name
  policy_arn = aws_iam_policy.lambda_model_policy.arn
}

data "aws_iam_policy_document" "lambda_model_policy" {
  source_policy_documents = [var.lambda_additional_policy]
  statement {
    sid       = "Logs"
    effect    = "Allow"
    resources = ["arn:aws:logs:*:*:*"]

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
  }
}

resource "aws_iam_policy" "lambda_model_policy" {
  name   = "${var.name}-lambda-model-policy"
  policy = data.aws_iam_policy_document.lambda_model_policy.json
}

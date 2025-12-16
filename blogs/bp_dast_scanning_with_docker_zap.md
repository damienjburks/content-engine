---
title: DAST Scanning with OWASP ZAP and Docker
slug: dast-scanning-owasp-zap-docker
subtitle: Performing DAST Scans Against Web Applications using OWASP ZAP and Docker
tags: docker, owasp, tutorial, cybersecurity
cover: https://cdn.hashnode.com/res/hashnode/image/upload/v1716749102373/crEwBst1E.png?auto=format
domain: damienjburks.hashnode.dev
saveAsDraft: true
enableToc: true
seriesSlug: sast-dast-docker
seriesName: SAST and DAST Scanning with Docker
---

## Introduction

Hey there, Damien here from DevSecBlueprint! In today’s blog post, we will be diving into DAST scanning with OWASP ZAP and Docker. If you’re just starting out with Dynamic Application Security Testing (DAST), I highly recommend watching my previous video on SAST and DAST concepts to lay down a foundational understanding.

Without further ado, let’s get right into the topic at hand.

## Prerequisites

Before we get started with the nuts and bolts of OWASP ZAP and Docker, there are a couple of prerequisites that need to be installed on your local machine:

1. **Docker**: We will be running OWASP ZAP in a Docker container.
2. **Git**: Required for cloning repositories.
3. **VS Code (Optional)**: It’s a helpful IDE for managing your code and version control history.

Having these installed will make the process smoother and more efficient.

## What is OWASP ZAP?

OWASP ZAP (Zed Attack Proxy) is a highly popular open-source penetration testing tool designed to help developers and security professionals find vulnerabilities in their web applications. Key features of OWASP ZAP include:

- Identifies a wide range of vulnerabilities, including those within the OWASP Top 10 such as security misconfigurations, SQL injection, and cross-site scripting.
- Capable of both **Active** and **Passive** scans.

### Active vs Passive Scans

Active and passive are two types of scanning modes in ZAP:

- **Passive Scans**: These scans check the HTTP request application's response for known indicators without attempting to penetrate the application.
- **Active Scans**: These scans actively inject requests that test for vulnerabilities, and are more effective but pose a risk of taking down the application.

![Active vs Passive Scans](path/to/Active-vs-Passive-Scans-diagram.png)

It’s recommended to use passive scans in a production environment to minimize risk.

## Docker Basics

Docker is a platform that allows us to package and run applications in an isolated environment called a container. This isolation offers several benefits, including security, ease of deployment, and the ability to run multiple containers simultaneously.

### Key Concepts

- **Container**: A lightweight standalone executable package that includes everything needed to run the application.
- **Dockerfile**: A text document containing instructions to build a Docker image.
- **Image**: A read-only template used to create Docker containers.

![Docker Architecture](path/to/Docker-architecture-diagram.png)

## Setup Instructions

### Cloning the Repository

First, you’ll need to clone the **TWAPP** web application repository:

```bash
git clone <repository-URL>
cd <cloned-repo-directory>
```

### Spinning Up the Environment

We will use Docker Compose to set up the necessary environment:

```bash
docker-compose up -d
```

The `-d` flag runs the container in detached mode, but if you want to see real-time logs, you can run:

```bash
docker-compose up
```

### Verifying the Setup

To ensure the environment is up and running, navigate to `http://localhost` in your web browser.

### Executing the Scan

Now, let’s run an OWASP ZAP scan using Docker. The following command mounts your current directory to the Docker container and runs a full active scan:

For Windows:

```powershell
docker run -v %cd%:/zap/wrk/:rw --network="host" owasp/zap2docker-stable zap-full-scan.py -t http://localhost -g gen.conf
```

For Mac/Linux:

```sh
docker run -v $(pwd):/zap/wrk/:rw --network="host" owasp/zap2docker-stable zap-full-scan.py -t http://localhost -g gen.conf
```

This command will:

1. Mount your current directory to the container.
2. Allow the ZAP Docker container to interact with your localhost.
3. Perform a full active scan and generate a report.

This process may take some time, so be patient.

![Docker and ZAP Integration](path/to/Docker-ZAP-Integration-diagram.png)

## Understanding the Scan Report

Once the scan is complete, you’ll find the generated report in HTML format:

```bash
ls zap_report.html
```

Open `zap_report.html` in a web browser:

![ZAP Scan Report Overview](path/to/ZAP-scan-report-overview.png)

### Interpreting the Report

The report will provide a summary of the identified alerts, their risk levels, and instances. Here are a few common vulnerabilities you might find:

- **SQL Injection**:

  - **Risk Level**: High
  - **Description**: Application source code disclosed due to improper handling of user inputs.
  - **Solution**: Ensure proper sanitization and parameterization of SQL queries.

- **Application Error Disclosure**:
  - **Risk Level**: Medium
  - **Description**: Error messages disclosing sensitive information.
  - **Solution**: Suppress or customize error messages to avoid revealing internal details.

![SQL Injection Details](path/to/SQL-Injection-Details.png)

## Conclusion

Thank you for following along with this comprehensive guide on DAST scanning using OWASP ZAP and Docker. We covered everything from setting up the environment to running scans and interpreting the results.

If you have any questions, comments, or feedback, feel free to reach out. Don’t forget to like, subscribe, and comment on my channel. Stay tuned for more insightful content!

_Happy Scanning!_

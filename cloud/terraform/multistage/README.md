### order

# Multistage Terraform Deployment

# note from AWS about EKS AMIs

You are receiving this message because you currently have 1 or more Amazon EKS clusters running Amazon Linux 2 (AL2) based AMIs. Amazon EKS will end support for EKS optimized AL2 AMIs on November 26, 2025.

To avoid any disruptions, please migrate your workloads to alternative AMI types before November 26, 2025. While you can continue using EKS AL2 AMIs, EKS will no longer release any new Kubernetes versions or updates to AL2 AMIs after this EOS date, including minor releases, patches, and bug fixes.

A list of your affected resource(s) can be found in the 'Affected resources' tab of your AWS Health Dashboard.

We recommend upgrading to Amazon Linux 2023 (AL2023) or Bottlerocket AMIs. AL2023 enables a secure-by-default approach with preconfigured security policies, SELinux in permissive mode, IMDSv2-only mode enabled by default, optimized boot times, and improved package management for enhanced security and performance, well-suited for infrastructure requiring significant customizations like direct OS-level access or extensive node changes. Bottlerocket enables enhanced security, faster boot times, and a smaller attack surface for improved efficiency with its purpose-built, container-optimized design, well-suited for container-native approaches with minimal node customizations. Additionally, you can build custom EKS AL2-optimized and AL2-accelerated AMIs [1] until the EOS date (November 26, 2025), or build a custom AMI with an Amazon Linux 2 base instance until the Amazon Linux 2 EOS date (June 30, 2026).

For more information, please visit AL2023 FAQs [2], Bottlerocket FAQs [3], or refer to Amazon Linux 2 to Amazon Linux 2023 [4] or Bottlerocket AMIs [5] documentation for detailed migration guidance.

If you have questions or any challenges taking action by November 26, 2025, please see EKS AL2 & AL2-Accelerated AMIs EOS FAQs [6] or contact AWS Support [7].

[1] https://urldefense.com/v3/__https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-build-scripts.html__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TOsthmFhg$
[2] https://urldefense.com/v3/__https://aws.amazon.com/linux/amazon-linux-2023/faqs/__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TMwKuJ0aw$
[3] https://urldefense.com/v3/__https://aws.amazon.com/bottlerocket/faqs/__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TNRxvJPAg$
[4] https://urldefense.com/v3/__https://docs.aws.amazon.com/eks/latest/userguide/al2023.html__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TPNyh7A9g$
[5] https://urldefense.com/v3/__https://docs.aws.amazon.com/eks/latest/userguide/eks-optimized-ami-bottlerocket.html__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TNeFHZiIg$
[6] https://urldefense.com/v3/__https://docs.aws.amazon.com/eks/latest/userguide/eks-ami-deprecation-faqs.html__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TMqSuNnUQ$
[7] https://urldefense.com/v3/__https://aws.amazon.com/support__;!!ADdU39pX!VVDATMwomIvumzHnrbe-KQZM_VQ5pibgvacmTwzrO7I-31XH2PEqIYGjaS91NCyxMdiFFM26XeKJ8TMUuwnuMQ$

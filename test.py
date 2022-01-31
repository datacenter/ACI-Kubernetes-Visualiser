import re
### Use this space to try out ideas and free code ###
def check_image_pull_secret(config):
    # Check if the image_pull_secret is valid
    image_pull_secret = config["registry"]["image_pull_secret"]
    print(image_pull_secret)
    # This is the regex used by kubect to validate objects names
    pattern = re.compile("[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*")
    if not pattern.fullmatch(str(image_pull_secret)):
        return False
    return True


testing={"registry":
         {"image_pull_secret" : "cluster-agent-secret-t44t3tfgdswfvfwe3tggbm"
         }
        }


if not check_image_pull_secret(testing):
    print("Invalid image_pull_secret: The image_pull_secret is the name of the K8s secret")
    
else:
    print("okay it passed smoothly")
    

# ISSUES

- When you select the partition, the region list should be updated. DONE
- There should be a global config stored in profile in some format that doesn't require 3rd party lib with the most
  recently selected profile, partition and region so they're auto loaded on app open. Maybe done?
- ECS status for Services is wrong, always shows blank status, 0 running tasks, 0 pending, 0 active. (when pointed at
  live aws)
- Filling in the jmes path does nothing even after clicking refresh? Maybe need a "Execute JMESPath" button. Yeah, I
  see, if I click enter, it responds, but I want a button- DONE I think
- Looks like we have a global problem with paging that only becomes obvious when working with live AWS... Can't request
  next page anywhere. Pretty much anything that returns a list needs to be able to indicate if there is a next page and
  to navigate to first, next, previous, last.
  Secrets for example, appear capped at 10. Other don't seem to be capped or have a higher default limit.
- KMS Key list only shows id, arn, "enabled" (incorrectly no). When you Describe key, you get a popup, which you ahve to
  click execute and then the grid only shows 1 key!
- View KMS key button on Aurora/Clusters does nothing even though the cluster detail shows kms_key_id
- SQS ARn is missing in SQS detail
- IAM Policies should have a quick filter for attachment_count>0
- IAM "Get Policy" doesn't show contents of policy? That should be most interesting thing.

- Need option for "no profile", once I select a profile, I can't unselect a profile. - DONE
- When I click start moto, it should clear the cache and set profile to no profile. Same for start robotocore.- DONE
  It is important that moto info and real aws info never get mixed up and the user not get mixed up (say with a live aws
  profile and thinking they're connected to moto)

ROADMAP

- Safety feature
    - enable deletes button to enable delete buttons across the app
    - enable changes to enable change buttons across the app
    - Doesn't change confirm request
- JMES Path query builder
import hashlib
import json
import logging
import os
import pprint
import re
import tempfile
import zipfile
from xml.etree import ElementTree

import arrow
import jinja2
import yaml
from scriptworker.exceptions import TaskVerificationError
from scriptworker.utils import get_results_and_future_exceptions, raise_future_exceptions

from beetmoverscript.constants import (
    ARTIFACT_REGISTRY_ACTIONS,
    DIRECT_RELEASE_ACTIONS,
    HASH_BLOCK_SIZE,
    MAVEN_ACTIONS,
    NORMALIZED_FILENAME_PLATFORMS,
    PARTNER_REPACK_ACTIONS,
    PRODUCT_TO_PATH,
    PROMOTION_ACTIONS,
    RELEASE_ACTIONS,
)

log = logging.getLogger(__name__)


JINJA_ENV = jinja2.Environment(loader=jinja2.PackageLoader("beetmoverscript"), undefined=jinja2.StrictUndefined)


def get_hash(filepath, hash_type="sha512"):
    """Function to return the digest hash of a file based on filename and
    algorithm"""
    digest = hashlib.new(hash_type)
    with open(filepath, "rb") as fobj:
        while True:
            chunk = fobj.read(HASH_BLOCK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def get_size(filepath):
    """Function to return the size of a file based on filename"""
    return os.path.getsize(filepath)


class BadXPIFile(Exception):
    def __init__(self, filepath):
        super().__init__("Error loading XPI data from " + filepath)


def get_addon_data(filepath):
    name = None
    version = None
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(filepath, "r") as zf:
        zf.extractall(tmpdir)
    rdf_path = os.path.join(tmpdir, "install.rdf")
    manifest_path = os.path.join(tmpdir, "manifest.json")
    if os.path.exists(rdf_path):
        rdf = ElementTree.parse(rdf_path)
        description = rdf.getroot()[0]
        for child in description:
            if child.tag.endswith("id"):
                name = child.text
            if child.tag.endswith("version"):
                version = child.text
    elif os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.loads(f.read())
            name = manifest.get("applications", {}).get("gecko", {}).get("id")
            version = manifest.get("version")
    else:
        raise BadXPIFile(filepath)
    if not name or not version:
        raise BadXPIFile(filepath)
    return {"name": name, "version": version}


def load_json(path):
    """Function to load a json from a file"""
    with open(path, "r") as fh:
        return json.load(fh)


def write_json(path, contents):
    """Function to dump a json content to a file"""
    with open(path, "w") as fh:
        json.dump(contents, fh, indent=4)


def write_file(path, contents):
    """Function to dump some string contents to a file"""
    with open(path, "w") as fh:
        fh.write(contents)


def is_release_action(action):
    """Function to return boolean if we're publishing a release as opposed to a
    nightly release or something else. Does that by checking the action type.
    """
    return action in RELEASE_ACTIONS


def is_direct_release_action(action):
    """Function to return boolean if we're publishing a release as opposed to a
    promoting to candidates and mirror then.Does that by checking the action type.
    """
    return action in DIRECT_RELEASE_ACTIONS


def is_promotion_action(action):
    """Function to return boolean if we're promoting a release as opposed to a
    nightly or something else. Does that by checking the action type.
    """
    return action in PROMOTION_ACTIONS


def is_partner_action(action):
    """Function to return boolean if we're promoting a release as opposed to a
    nightly or something else. Does that by checking the action type.
    """
    return action in PARTNER_REPACK_ACTIONS


def is_import_artifacts_action(action):
    return action in ARTIFACT_REGISTRY_ACTIONS


def is_maven_action(action):
    """Function to return boolean if the task intends to upload onto maven.
    Geckoview uploads to maven, for instance. Does that by checking the action type.
    """
    return action in MAVEN_ACTIONS


def is_partner_private_task(context):
    """Function to return boolean if we're considering a public partner task.
    Does that by checking the action type and presence of a flag in payload
    """
    return is_partner_action(context.action) and "partner" in context.bucket


def is_partner_public_task(context):
    """Function to return boolean if we're considering a private partner task.
    Does that by checking the action type and absence of a flag in payload
    """
    return is_partner_action(context.action) and "partner" not in context.bucket


def get_product_name(task, config, lowercase_app_name=True):
    # importing in-function to avoid circular dependency problems
    from beetmoverscript.task import get_release_props, get_task_action

    action = get_task_action(task, config)

    if action == "push-to-releases":
        if "product" not in task["payload"]:
            raise ValueError("product not found in task payload.")
        return task["payload"]["product"].lower()

    if "releaseProperties" not in task["payload"]:
        raise ValueError("releaseProperties not found in task payload.")

    if "appName" not in task["payload"]["releaseProperties"]:
        raise ValueError("appName not found in task payload.")

    release_props = get_release_props(task)
    appName = task["payload"]["releaseProperties"]["appName"]
    if lowercase_app_name:
        appName = appName.lower()

    # XXX: this check is helps reuse this function in both
    # returning the proper templates file but also for the release name in
    # Balrog manifest that beetmover is uploading upon successful run
    for dynamic_platform in ("devedition", "pinebuild"):
        if dynamic_platform in release_props["stage_platform"]:
            if appName[0].isupper():
                return dynamic_platform.capitalize()
            else:
                return dynamic_platform

    return appName


def generate_beetmover_template_args(context):
    task = context.task
    release_props = context.release_props

    upload_date = task["payload"]["upload_date"]
    args = []
    try:
        upload_date = float(upload_date)
    except ValueError:
        upload_date = upload_date.split("/")[-1]
        args.append("YYYY-MM-DD-HH-mm-ss")

    tmpl_args = {
        # payload['upload_date'] is a timestamp defined by params['pushdate']
        # in mach taskgraph
        "upload_date": arrow.get(upload_date, *args).format("YYYY/MM/YYYY-MM-DD-HH-mm-ss"),
        "version": release_props["appVersion"],
        "branch": release_props["branch"],
        "product": release_props["appName"],
        "stage_platform": release_props["stage_platform"],
        "platform": release_props["platform"],
        "buildid": release_props["buildid"],
        "partials": get_partials_props(task),
        "filename_platform": NORMALIZED_FILENAME_PLATFORMS.get(release_props["stage_platform"], release_props["stage_platform"]),
    }

    if is_promotion_action(context.action) or is_release_action(context.action) or is_partner_action(context.action):
        tmpl_args["build_number"] = task["payload"]["build_number"]
        tmpl_args["version"] = task["payload"]["version"]

    # e.g. action = 'push-to-candidates' or 'push-to-nightly'
    tmpl_bucket = context.action.split("-")[-1]

    locales_in_upstream_artifacts = [upstream_artifact["locale"] for upstream_artifact in task["payload"]["upstreamArtifacts"] if "locale" in upstream_artifact]
    uniques_locales_in_upstream_artifacts = sorted(list(set(locales_in_upstream_artifacts)))

    if "locale" in task["payload"] and uniques_locales_in_upstream_artifacts:
        _check_locale_consistency(task["payload"]["locale"], uniques_locales_in_upstream_artifacts)
        tmpl_args["locales"] = uniques_locales_in_upstream_artifacts
    elif uniques_locales_in_upstream_artifacts:
        tmpl_args["locales"] = uniques_locales_in_upstream_artifacts
    elif "locale" in task["payload"]:
        tmpl_args["locales"] = [task["payload"]["locale"]]

    product_name = get_product_name(task, context.config)
    if tmpl_args.get("locales") and (
        # we only apply the repacks template if not english or android "multi" locale
        set(tmpl_args.get("locales")).isdisjoint({"en-US", "multi"})
    ):
        tmpl_args["template_key"] = "%s_%s_repacks" % (product_name, tmpl_bucket)
    else:
        tmpl_args["template_key"] = "%s_%s" % (product_name, tmpl_bucket)

    return tmpl_args


def _check_locale_consistency(locale_in_payload, uniques_locales_in_upstream_artifacts):
    if len(uniques_locales_in_upstream_artifacts) > 1:
        raise TaskVerificationError(
            '`task.payload.locale` is defined ("{}") but too many locales set in \
`task.payload.upstreamArtifacts` ({})'.format(
                locale_in_payload, uniques_locales_in_upstream_artifacts
            )
        )
    elif len(uniques_locales_in_upstream_artifacts) == 1:
        locale_in_upstream_artifacts = uniques_locales_in_upstream_artifacts[0]
        if locale_in_payload != locale_in_upstream_artifacts:
            raise TaskVerificationError(
                '`task.payload.locale` ("{}") does not match the one set in \
`task.payload.upstreamArtifacts` ("{}")'.format(
                    locale_in_payload, locale_in_upstream_artifacts
                )
            )


def generate_beetmover_manifest(context):
    """
    generates and outputs a manifest that maps expected Taskcluster artifact names
    to release deliverable names
    """
    tmpl_args = generate_beetmover_template_args(context)

    tmpl_name = "{}.yml".format(tmpl_args["template_key"])
    jinja_env = JINJA_ENV
    tmpl = jinja_env.get_template(tmpl_name)

    log.info("generating manifest from: {}".format(tmpl.filename))

    manifest = yaml.safe_load(tmpl.render(**tmpl_args))

    log.info("manifest generated:")
    log.info(pprint.pformat(manifest))

    return manifest


def get_partials_props(task):
    """Examine contents of task.json (stored in context.task) and extract
    partials mapping data from the 'extra' field"""
    partials = task.get("extra", {}).get("partials", {})
    return {p["artifact_name"]: p for p in partials}


def get_candidates_prefix(product, version, build_number):
    return "{}candidates/{}-candidates/build{}/".format(PRODUCT_TO_PATH[product], version, str(build_number))


def get_releases_prefix(product, version):
    return "{}releases/{}/".format(PRODUCT_TO_PATH[product], version)


def get_partner_candidates_prefix(prefix, partner):
    return "{}partner-repacks/{}/v1/".format(prefix, partner)


def get_partner_releases_prefix(product, version, partner):
    return "{}releases/partners/{}/{}/".format(PRODUCT_TO_PATH[product], partner, version)


def matches_exclude(keyname, excludes):
    for exclude in excludes:
        if re.search(exclude, keyname):
            return True
    return False


def get_partner_match(keyname, candidates_prefix, partners):
    for partner in partners:
        if keyname.startswith(get_partner_candidates_prefix(candidates_prefix, partner)):
            return partner
    return None


def get_bucket_name(context, product, cloud):
    return context.config["clouds"][cloud][context.bucket]["product_buckets"][product.lower()]


def get_resource_name(context, product, cloud):
    if context.resource_type == "apt-repo":
        return context.config["clouds"][cloud][context.bucket]["product_apt_repos"][product.lower()]
    if context.resource_type == "yum-repo":
        return context.config["clouds"][cloud][context.bucket]["product_yum_repos"][product.lower()]
    if context.resource_type == "bucket":
        return context.config["clouds"][cloud][context.bucket]["product_buckets"][product.lower()]
    raise Exception("No valid resource type in task scopes. Resource must be one of [apt-repo, yum-repo, bucket]")


def get_fail_task_on_error(clouds_config, release_bucket, cloud):
    return clouds_config[cloud][release_bucket].get("fail_task_on_error")


async def await_and_raise_uploads(cloud_uploads, clouds_config, release_bucket):
    for cloud in cloud_uploads:
        if len(cloud_uploads[cloud]) == 0:
            continue
        if get_fail_task_on_error(clouds_config, release_bucket, cloud):
            await raise_future_exceptions(cloud_uploads[cloud])
        else:
            _, ex = await get_results_and_future_exceptions(cloud_uploads[cloud])
            # Print out the exceptions
            for e in ex:
                log.warning("Skipped exception:")
                print(e.__traceback__)
                print(getattr(e, "message", "<no message>"))


def get_credentials(context, cloud):
    clouds = context.config["clouds"]
    if cloud not in clouds:
        raise ValueError(f"{cloud} not a valid cloud [{clouds.keys()}]")
    if context.bucket not in clouds[cloud]:
        return
    return clouds[cloud][context.bucket]["credentials"]


def get_url_prefix(context):
    if context.bucket not in context.config["url_prefix"]:
        raise ValueError(f"No bucket config found for {context.bucket}")

    return context.config["url_prefix"][context.bucket]


def validated_task_id(task_id):
    """Validate the format of a taskcluster taskId."""
    pattern = r"^[A-Za-z0-9_-]{8}[Q-T][A-Za-z0-9_-][CGKOSWaeimquy26-][A-Za-z0-9_-]{10}[AQgw]$"
    if re.fullmatch(pattern, task_id):
        return task_id
    raise ValueError("No valid taskId found.")


def exists_or_endswith(filename, basenames):
    if isinstance(basenames, str):
        basenames = [basenames]
    for artifact in basenames:
        if filename == artifact or filename.endswith(artifact):
            return True
    return False


def extract_full_artifact_map_path(artifact_map, basepath, locale):
    """Find the artifact map entry from the given path."""
    for entry in artifact_map:
        if entry["locale"] != locale:
            continue
        for path in entry["paths"]:
            if path.endswith(basepath):
                return path


def extract_file_config_from_artifact_map(artifact_map, path, task_id, locale):
    """Return matching artifact map config."""
    for entry in artifact_map:
        if entry["taskId"] != task_id or entry["locale"] != locale:
            continue
        if not entry["paths"].get(path):
            continue
        return entry["paths"][path]
    raise TaskVerificationError("No artifact map entry for {}/{} {}".format(task_id, locale, path))

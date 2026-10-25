"""
Stops automatic programs from sending the public forms.

People never see the extra field. A program that fills every box usually
fills that one too, so we throw the message away. A real person also needs
a couple of seconds to type, so an instant send is rejected.
"""
import time

from rest_framework import serializers

# Long enough that a script is too fast, short enough that a person is not blocked.
MIN_SECONDS = 2
# A form left open all day can still be sent. Older than this is ignored.
MAX_SECONDS = 60 * 60 * 12


class BotCheckMixin(serializers.Serializer):
    """Add this to a form serializer. The two fields are not saved.

    It has to be a serializer, not a plain class, or Django drops the two
    extra fields and every real submission is rejected.
    """

    # Hidden on the page. Must stay empty.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    # When the form first appeared, in milliseconds. Sent by the browser.
    form_started = serializers.IntegerField(write_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        website = (attrs.pop("website", "") or "").strip()
        started = attrs.pop("form_started", None)

        if website:
            raise serializers.ValidationError("We could not send that. Please try again.")

        if started is None or started < 0:
            raise serializers.ValidationError("We could not send that. Please try again.")

        # started is milliseconds. A clock a few seconds ahead is still a person.
        now_ms = time.time() * 1000
        if started > now_ms + 30_000:
            raise serializers.ValidationError("We could not send that. Please try again.")

        elapsed = (now_ms - started) / 1000
        if elapsed < MIN_SECONDS:
            raise serializers.ValidationError("Please wait a moment and try again.")
        if elapsed > MAX_SECONDS:
            raise serializers.ValidationError("This form has been open too long. Refresh the page and try again.")
        return attrs

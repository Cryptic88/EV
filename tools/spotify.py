"""Spotify-only Windows media controls; search opens Spotify's own results."""
import asyncio
import json
import os
from urllib.parse import quote


class SpotifyTools:
    def spotify(self, action, query=''):
        if action == 'search':
            if not query.strip():
                raise ValueError('Provide a song, artist or playlist to search for.')
            os.startfile('spotify:search:' + quote(query.strip(), safe=''))
            return f'Opened Spotify search for {query}. No track has been selected yet.'
        if action not in {'play', 'pause', 'next', 'previous', 'status'}:
            raise ValueError('Spotify actions: search, play, pause, next, previous, status.')
        return asyncio.run(self._control(action))

    async def _control(self, action):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager
        manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
        sessions = [s for s in manager.get_sessions()
                    if 'spotify' in s.source_app_user_model_id.casefold()]
        if len(sessions) != 1:
            return 'Open Spotify and select a track first; a unique Spotify playback session is required.'
        session = sessions[0]
        if action == 'status':
            media = await session.try_get_media_properties_async()
            return json.dumps({'title': media.title, 'artist': media.artist,
                               'state': str(session.get_playback_info().playback_status)})
        method = {'play': 'try_play_async', 'pause': 'try_pause_async',
                  'next': 'try_skip_next_async', 'previous': 'try_skip_previous_async'}[action]
        accepted = await getattr(session, method)()
        return f'Spotify {action} accepted.' if accepted else f'Spotify did not accept {action}.'

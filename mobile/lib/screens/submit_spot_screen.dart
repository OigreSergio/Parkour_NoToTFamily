import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';

import '../providers.dart';
import '../repositories/spot_repository.dart';

/// Report a spot: what it is, where it is, and at least three photos of it.
///
/// The photos are the point of the form. A spot nobody can see is a spot no
/// moderator can verify, so the send button stays off until there are
/// [SpotRepository.minPhotos] of them. What is sent goes into the moderation
/// queue (`status = pending`), it does not appear on the map straight away.
class SubmitSpotScreen extends ConsumerStatefulWidget {
  const SubmitSpotScreen({super.key});

  @override
  ConsumerState<SubmitSpotScreen> createState() => _SubmitSpotScreenState();
}

class _SubmitSpotScreenState extends ConsumerState<SubmitSpotScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _description = TextEditingController();
  final _picker = ImagePicker();

  final List<SpotPhotoUpload> _photos = [];
  LatLng? _position;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    // The spot is usually where you are standing when you report it.
    _position = ref.read(currentLocationProvider).valueOrNull;
  }

  @override
  void dispose() {
    _name.dispose();
    _description.dispose();
    super.dispose();
  }

  bool get _hasEnoughPhotos => _photos.length >= SpotRepository.minPhotos;

  Future<void> _addPhotos() async {
    final picked = await _picker.pickMultiImage(imageQuality: 85);
    if (picked.isEmpty) return;

    final added = <SpotPhotoUpload>[];
    for (final file in picked) {
      added.add(
        SpotPhotoUpload(
          bytes: await file.readAsBytes(),
          filename: file.name,
          contentType: file.mimeType ?? 'image/jpeg',
        ),
      );
    }
    if (!mounted) return;
    setState(() => _photos.addAll(added));
  }

  Future<void> _useMyPosition() async {
    final position = await ref.read(locationServiceProvider).currentLatLng();
    if (!mounted) return;
    setState(() => _position = position);
  }

  Future<void> _submit() async {
    final session = ref.read(sessionProvider);
    if (!session.isSignedIn) {
      setState(() => _error = 'Sign in first — a report belongs to an account.');
      return;
    }
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (!_hasEnoughPhotos || _position == null) return;

    setState(() {
      _sending = true;
      _error = null;
    });

    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    try {
      final spot = await ref.read(sessionProvider.notifier).submitSpot(
            name: _name.text.trim(),
            description: _description.text.trim(),
            position: _position!,
            photos: _photos,
          );
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            '“${spot.name}” sent. It goes on the map once a moderator '
            'verifies it.',
          ),
        ),
      );
      navigator.pop();
    } catch (error) {
      if (mounted) {
        setState(() => _error = '$error');
      }
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final position = _position;
    final signedIn = ref.watch(sessionProvider).isSignedIn;

    return Scaffold(
      appBar: AppBar(title: const Text('Report a spot')),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            if (!signedIn)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: _Notice(
                  icon: Icons.person_outline,
                  text: 'Sign in to send a report — with your email, or as a '
                      'guest from the account menu.',
                ),
              ),
            TextFormField(
              controller: _name,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'Name of the spot',
                hintText: 'Piazza with low walls and rails',
                border: OutlineInputBorder(),
              ),
              validator: (value) => (value ?? '').trim().length < 2
                  ? 'Give the spot a name'
                  : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _description,
              minLines: 3,
              maxLines: 6,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                labelText: 'What is there',
                hintText: 'Surfaces, obstacles, heights, ground, how busy it '
                    'is, anything that helps someone who has never been.',
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
              validator: (value) => (value ?? '').trim().length < 10
                  ? 'Describe what a traceur finds there'
                  : null,
            ),
            const SizedBox(height: 20),

            Text('Where it is', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            Card(
              margin: EdgeInsets.zero,
              child: ListTile(
                leading: const Icon(Icons.place_outlined),
                title: Text(
                  position == null
                      ? 'No position yet'
                      : '${position.latitude.toStringAsFixed(5)}, '
                          '${position.longitude.toStringAsFixed(5)}',
                ),
                subtitle: Text(
                  position == null
                      ? 'Stand at the spot and use your position.'
                      : 'Taken from your device.',
                ),
                trailing: TextButton.icon(
                  onPressed: _sending ? null : _useMyPosition,
                  icon: const Icon(Icons.my_location, size: 18),
                  label: const Text('Use my position'),
                ),
              ),
            ),
            const SizedBox(height: 20),

            Row(
              children: [
                Expanded(
                  child: Text('Photos', style: theme.textTheme.titleMedium),
                ),
                Text(
                  '${_photos.length}/${SpotRepository.minPhotos} minimum',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: _hasEnoughPhotos
                        ? theme.colorScheme.primary
                        : theme.colorScheme.error,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            _PhotoStrip(
              photos: _photos,
              onAdd: _sending ? null : _addPhotos,
              onRemove: _sending
                  ? null
                  : (index) => setState(() => _photos.removeAt(index)),
            ),
            const SizedBox(height: 8),
            Text(
              'At least ${SpotRepository.minPhotos} photos: without them nobody '
              'can verify the spot. Show the obstacles, the ground and the way in.',
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.outline),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              _Notice(icon: Icons.error_outline, text: _error!, isError: true),
            ],

            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed:
                  _sending || !_hasEnoughPhotos || position == null || !signedIn
                      ? null
                      : _submit,
              icon: _sending
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send_outlined),
              label: Text(_sending ? 'Sending…' : 'Send for review'),
            ),
            const SizedBox(height: 8),
            Text(
              'Reports are moderated: the spot appears on the map once the '
              'family verifies it.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.outline),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

/// The picked photos, plus the tile that adds more.
class _PhotoStrip extends StatelessWidget {
  const _PhotoStrip({
    required this.photos,
    required this.onAdd,
    required this.onRemove,
  });

  final List<SpotPhotoUpload> photos;
  final VoidCallback? onAdd;
  final void Function(int index)? onRemove;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SizedBox(
      height: 110,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: photos.length + 1,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          if (index == photos.length) {
            return InkWell(
              onTap: onAdd,
              borderRadius: BorderRadius.circular(12),
              child: Container(
                width: 110,
                decoration: BoxDecoration(
                  border: Border.all(color: theme.colorScheme.outlineVariant),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.add_a_photo_outlined),
                    SizedBox(height: 6),
                    Text('Add photos'),
                  ],
                ),
              ),
            );
          }
          return Stack(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.memory(
                  photos[index].bytes,
                  width: 110,
                  height: 110,
                  fit: BoxFit.cover,
                ),
              ),
              Positioned(
                top: 2,
                right: 2,
                child: IconButton.filledTonal(
                  visualDensity: VisualDensity.compact,
                  onPressed:
                      onRemove == null ? null : () => onRemove!.call(index),
                  icon: const Icon(Icons.close, size: 16),
                  tooltip: 'Remove photo',
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

/// A short message box, for the sign-in hint and for errors.
class _Notice extends StatelessWidget {
  const _Notice({required this.icon, required this.text, this.isError = false});

  final IconData icon;
  final String text;
  final bool isError;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final background =
        isError ? theme.colorScheme.errorContainer : theme.colorScheme.secondaryContainer;
    final foreground = isError
        ? theme.colorScheme.onErrorContainer
        : theme.colorScheme.onSecondaryContainer;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(icon, color: foreground),
          const SizedBox(width: 10),
          Expanded(
            child: Text(text,
                style: theme.textTheme.bodySmall?.copyWith(color: foreground)),
          ),
        ],
      ),
    );
  }
}

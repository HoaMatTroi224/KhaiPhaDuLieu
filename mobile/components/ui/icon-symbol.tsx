// Fallback for using MaterialIcons on Android and web.

import MaterialIcons from '@expo/vector-icons/MaterialIcons';
import { SymbolViewProps, SymbolWeight } from 'expo-symbols';
import { ComponentProps } from 'react';
import { OpaqueColorValue, type StyleProp, type TextStyle } from 'react-native';

type IconMapping = Record<SymbolViewProps['name'], ComponentProps<typeof MaterialIcons>['name']>;
type IconSymbolName = keyof typeof MAPPING;

/**
 * Add your SF Symbols to Material Icons mappings here.
 * - see Material Icons in the [Icons Directory](https://icons.expo.fyi).
 * - see SF Symbols in the [SF Symbols](https://developer.apple.com/sf-symbols/) app.
 */
const MAPPING = {
  'house.fill': 'home',
  'paperplane.fill': 'send',
  'chevron.left.forwardslash.chevron.right': 'code',
  'chevron.right': 'chevron-right',
  'star.fill': 'star',
  'books.vertical.fill': 'library-books',
  'text.bubble.fill': 'chat-bubble',
  'plus.circle.fill': 'add-circle',
  'person.fill': 'person',
  'cloud_upload': 'cloud-upload',
  'picture_as_pdf': 'picture-as-pdf',
  'document_scanner': 'document-scanner',
  'description': 'description',
  'attachment': 'attach-file',
  'send.fill': 'send',
  'cloud.download.fill': 'cloud-download',
  'history': 'history',
  'download_done': 'download-done',
  'ellipsis': 'more-vert',
  'more_vert': 'more-vert',
  'auto_awesome': 'auto-awesome',
  'cloud_done': 'cloud-done',
  'bolt': 'bolt',
} as const;

//type IconSymbolName = keyof typeof MAPPING;

/**
 * An icon component that uses native SF Symbols on iOS, and Material Icons on Android and web.
 * This ensures a consistent look across platforms, and optimal resource usage.
 * Icon `name`s are based on SF Symbols and require manual mapping to Material Icons.
 */
export function IconSymbol({
  name,
  size = 24,
  color,
  style,
}: {
  name: IconSymbolName;
  size?: number;
  color: string | OpaqueColorValue;
  style?: StyleProp<TextStyle>;
  weight?: SymbolWeight;
}) {
  const iconName = MAPPING[name] as ComponentProps<typeof MaterialIcons>['name'];

  return <MaterialIcons color={color} size={size} name={iconName} style={style} />;
}

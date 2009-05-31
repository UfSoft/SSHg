

function readable_size(elem_id, bytes) {
  bytes = parseFloat(bytes) || 0.0;
  $(elem_id).val(bytes.toFixed(0));
  if ( bytes == 0.0 ) {
    return '( unlimited size )';
  };
  var unit;
  var units = ['bytes', 'KB', 'MB', 'GB', 'TB']; //, 'PB', 'EB', 'ZB', 'YB'];
  for ( idx=1; idx < units.length-1; idx++ ) {
    if ( bytes < 1024 ) break;
    unit = idx;
    bytes /= 1024;
  };
  return '( ' + bytes.toFixed(2) + ' ' + units[unit || 0] + ' )';
};


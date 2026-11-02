// Meta OS attract screen: spinning Meta loop, ASCII frames.
// Source: the product's own renderer, js/logo-background.js —
// its ribbon path (loopPoint), surface (buildSurface), lighting
// (diffuse + specular + rim over the GLYPHS ramp), and Y-axis
// spin, rasterized offline onto the 46x17 console grid. The
// only adaptations are the grid size and Y_PROJECTION, which
// the source recomputes per viewport (text cells ~2:1).
// Data only; the console idle task cycles FRAMES on a timer and
// exits on any keypress.
pub const FRAME_W: usize = 46;
pub const FRAME_H: usize = 17;
pub static FRAMES: &[&str] = &[
    "



                             h552AXXs
           h552AAAA2      HH3MMMh5XXsX
         ShMHSMAAAA225  H3hHGSMMh2XXXX
         BG#@9i A225553HhMHSHHM  :XXXXX
        @S9@@B     53M3MMSHHH     XXXXX
        @9@@@:     MMMMGMMHG     2XXXAX
        @@@@@@  MMMhMMHMHGS##&  :AXXAA
         @@@@GMM53MMHMM GS9&@@@hAXAAAA
         @@@@&MMHHHMM      @@@@&522AA
           @@9B#MM            @SM3


",
    "



          Xssrrir              sr
         XXXXXsrrrr         MXsssii
        ;AXXAAXrrrsss     hXsXXXsii
        AXXAAA ;rsssss   XXsXXXXiii
        AXAAAA   rssssshXssXXX Aiir
        AAAAAA     sshXssXXX  5rirr
        iAAAA22    #XXsXXXX  @rrrr
         A2222552AXXsXXXXXAA2rsss
          2225335AXXXXXXXXAA22AX
           5533352AAA
               52

",
    "


              irr
             Sriri
             rirrii         2ir
             5rrri;;       hiii
             @rrrri;;     3i;i
             Arrrr;;;i    i;ii
             Arrrrs;iii Xi;;i
              Srrrssiiihi;;i;
              rrssssssriiii;
               Xssssssriiii
                ssssssrrr
                  ;ssss

",
    "


                   2AA2
                   2AXBr
                   2AX@@ A2X
                   ;;AXXsA22
                  2r  XXG222X
                  2X  5XXs222
                  2i  5XXs hs
                  2sshr X2shr
                  2ssir  Xsii
                   ssi   Xrri
                          iri
                          ;i

",
    "


                        55522A@
                      555552AAAAs
                    35555552AAAAAr
                  3355552r AAAAAAA
                  35555r2222 AAAAAr
                 32555i 55253AAAAAA
                32555r   5525MAAAAA;
                2222r     5525AAAAAr
                222:       555AAAAAr
                22;         552AAAA
                             522AA;


",
    "


                             @GSM3
                          &@@@@M5522
               @@#hMMM  9B&@@@@&522A22
             @@@@@H333SS##9&@@@h2222A2
            &&9&@@MMGGGSG#9i     222222
            BS#9   MHHHGSsM3     222222
           9GMG: hhMMMHHGMh3h    222222
           Gh3h53hhhMM  MhHh333  222222
           h355533hh;     HHMh352AAA222
           33555533         3h352AAA2A
            5555;             355222


",
    "



              AA             352AAXX
          35522AAA25      hM3hh35AXXX
         GhMHG3A22553h  H3hMMGS35AXXXX
        #HS#&G  253hMMMHhMHSMMh  XXXAA
        &SB@&      hMHhMHSHH     AAAAA
        @B@@@      HhMHGHH9B     AAAAA
        @@@@@   MM3HHSHHHB@@@@  AAAAAA
        @@@@@hHMMMHGMHH B@@@@@@52AAA2
         @@@@GMMHGSMM      @@@@H3222
          @@&#9H#H            @SM


",
    "



          Xsrrirr
        XXXXXXrrrss         Xsssri
        AXXAAXrrssss      5XssXXrir
        AAAAA  rsssXXX   XssXXXsiir
        AAAAA    rXXXXXhXsXXXX rrrr
        AAAA22     XX3XssXXX  Hrrr
        22A2222    :XssXXXXA ssrrs
        X22225332AXXXXXXXAAA2ssss
         X5255332AXXXXXXsAA225AX
           533335AAAAA
             3352AA

",
    "


             rrri
            Srrri;
            @rrri;;        iii
            Srrrs;;i       2ii
            Arrrs;iii     3iii
            ;Xsrssiiii    i;ii
             hsrsssiiii  2i;i
              5sssssiirr;iii;
              XsssssXX2ii;ii
               XssssXssiiii
                sssXXssrir
                  sXXsrr

",
    "


                   AX@
                  2AXX&
                  2AXXXX2AA
                  2r XX2rA22
                  2:  XXS222r
                  2;  5XXs223
                  2ir @sXAr2A
                  2sshr XAs2Xs
                   ssir  Asrir
                   i:i    Xrrr
                          srr
                           ii

",
    "


                       555222AA
                     5555522AAAAA
                    2555552AAAAAAs
                  322555i2  AAAXAAr
                 33255Xs222X AAAXAX
                 32252 52222# AAAXAr
                 2222i   52222AAXXAs
                3222;     55225XXXXA
                522s       5552XXXXX
                222         5552XXXX
                              52AAX;
                                2A

",
    "


                            99#H525
                         ##B@@@H322AA
               @@SH5h2 HGG##&@@@h2AAAA
             @@@@@M35hMHHHG#B&  2AAAAAA
            &@9@@@SHhhhMMHG      AAAAAA
            @#H#i  hhhhhM:h:      AAAAAA
            9HGr 5333hhhHMh3M:    AAAAAA
            Hhh5553333  MHGMh3h5  AAAAAr
            h3225553s     MGHh355AAAAAA
            3525555         hMh352AAAAA
             552;             335222A


",
];
